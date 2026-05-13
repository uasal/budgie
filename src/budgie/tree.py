from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Callable


class BudgetTreeError(Exception):
    """Raised when budget tree construction or rendering fails."""


@dataclass
class BudgetNode:
    name: str
    value: float | None
    allocation: float | None
    kind: str
    combine_op: str | None = None
    op_label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list["BudgetNode"] = field(default_factory=list)


@dataclass
class _CombineOpSpec:
    func: Callable[..., float]
    label_builder: Callable[[dict[str, Any]], str]


def _rss(values: list[float], **_: Any) -> float:
    if not values:
        raise BudgetTreeError("rss requires at least one child value.")
    return math.sqrt(sum(value**2 for value in values))


def _sum(values: list[float], **_: Any) -> float:
    return sum(values)


def _product(values: list[float], **_: Any) -> float:
    result = 1.0
    for value in values:
        result *= value
    return result


def _scalar_multiply(values: list[float], *, factor: float | None = None, **_: Any) -> float:
    if not values:
        raise BudgetTreeError("scalar_multiply requires at least one child value.")
    if factor is None:
        raise BudgetTreeError("scalar_multiply requires a factor.")
    if len(values) != 1:
        raise BudgetTreeError("scalar_multiply requires exactly one child value.")
    return values[0] * factor


def _max(values: list[float], **_: Any) -> float:
    if not values:
        raise BudgetTreeError("max requires at least one child value.")
    return max(values)


_COMBINE_OPS: dict[str, _CombineOpSpec] = {}


def _constant_label(default_label: str) -> Callable[[dict[str, Any]], str]:
    def label_builder(_: dict[str, Any]) -> str:
        return default_label

    return label_builder


def _scalar_multiply_label(metadata: dict[str, Any]) -> str:
    return rf"$\times {metadata.get('factor', '?')}$"


def register_combine_op(
    name: str,
    func: Callable[..., float],
    default_label: str | Callable[[dict[str, Any]], str],
) -> None:
    """Register a new combine operation."""
    if callable(default_label):
        label_builder = default_label
    else:
        label_builder = _constant_label(default_label)
    _COMBINE_OPS[name] = _CombineOpSpec(func=func, label_builder=label_builder)


register_combine_op("rss", _rss, r"$\sqrt{\sum c_i^2}$")
register_combine_op("sum", _sum, r"$\sum$")
register_combine_op("product", _product, r"$\prod$")
register_combine_op("scalar_multiply", _scalar_multiply, _scalar_multiply_label)
register_combine_op("max", _max, r"$\max$")


def _format_schema_error() -> str:
    return (
        "Missing required 'post_processing_chain'. Expected schema:\n"
        "post_processing_chain:\n"
        "  - op: <combine_op>\n"
        "    label: <node_label>\n"
        "    op_label: <edge_label>        # optional\n"
        "  - op: scalar_multiply           # for scale steps\n"
        "    factor: <number>              # or use factor_key\n"
        "    factor_key: <scalar_key>      # optional alternative\n"
        "    label: <node_label>"
    )


def _coerce_table_records(table: Any) -> list[dict[str, Any]]:
    if hasattr(table, "reset_index") and hasattr(table, "to_dict"):
        return table.reset_index().to_dict("records")
    if isinstance(table, list):
        return [dict(record) for record in table]
    raise BudgetTreeError("Unsupported table type. Provide a pandas-like table or list of records.")


def _resolve_table_and_config(
    budget_or_table: Any,
    config: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str] | None]:
    derived_config = config or {}
    adapter_field_map = None
    if hasattr(budget_or_table, "get_pandas_table"):
        table = budget_or_table.get_pandas_table()
        if not derived_config:
            if hasattr(budget_or_table, "budget") and isinstance(budget_or_table.budget, dict):
                derived_config = budget_or_table.budget
            elif hasattr(budget_or_table, "config") and isinstance(budget_or_table.config, dict):
                derived_config = budget_or_table.config
        records = _coerce_table_records(table)
        if records:
            columns = set(records[0].keys())
            inferred_cbe = next((column for column in columns if str(column).endswith(" CBE")), None)
            inferred_cbe_name = str(inferred_cbe) if inferred_cbe is not None else None
            inferred_prefix = inferred_cbe_name.rsplit(" CBE", 1)[0] if inferred_cbe_name else None
            inferred_allocation = (
                f"{inferred_prefix} Allocation"
                if inferred_prefix and f"{inferred_prefix} Allocation" in columns
                else None
            )
            if inferred_cbe and inferred_allocation and "Type" in columns:
                adapter_field_map = {"cbe": inferred_cbe, "allocation": inferred_allocation, "type": "Type"}
        return records, derived_config, adapter_field_map
    else:
        table = budget_or_table
    return _coerce_table_records(table), derived_config, adapter_field_map


def _resolve_factor(step: dict[str, Any], config: dict[str, Any], scalars: dict[str, Any] | None) -> float:
    if "factor" in step:
        return float(step["factor"])
    if "factor_key" in step:
        key = step["factor_key"]
        if scalars and key in scalars:
            return float(scalars[key])
        if key in config:
            return float(config[key])
        raise BudgetTreeError(f"Could not resolve factor_key '{key}' for scalar_multiply step.")
    raise BudgetTreeError("scalar_multiply step requires either 'factor' or 'factor_key'.")


def _leaf_name(record: dict[str, Any]) -> str:
    """Return best-effort leaf display name from common table field names."""
    for key in ("Name", "name", "Term", "term", "index", "Item", "item", "Description"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return "leaf"


def _compute_node_value(node: BudgetNode) -> tuple[float | None, float | None]:
    if not node.children or not node.combine_op:
        return node.value, node.allocation
    if node.combine_op not in _COMBINE_OPS:
        raise BudgetTreeError(f"Unsupported combine_op '{node.combine_op}'.")

    spec = _COMBINE_OPS[node.combine_op]

    value_children = [child.value for child in node.children if child.value is not None]
    alloc_children = [child.allocation for child in node.children if child.allocation is not None]
    factor = node.metadata.get("factor")

    if node.combine_op == "scalar_multiply":
        non_scalar_values = [child.value for child in node.children if child.kind != "scalar" and child.value is not None]
        non_scalar_alloc = [
            child.allocation for child in node.children if child.kind != "scalar" and child.allocation is not None
        ]
        value_children = non_scalar_values or value_children
        alloc_children = non_scalar_alloc or alloc_children

    computed_value = spec.func(value_children, factor=factor) if value_children else None
    computed_alloc = spec.func(alloc_children, factor=factor) if alloc_children else None
    return computed_value, computed_alloc


def _build_op_label(op: str, metadata: dict[str, Any], op_label: str | None) -> str | None:
    if op_label:
        return op_label
    if op in _COMBINE_OPS:
        return _COMBINE_OPS[op].label_builder(metadata)
    return None


def build_tree(
    budget_or_table: Any,
    *,
    config: dict[str, Any] | None = None,
    field_map: dict[str, str] | None = None,
    category_combine_ops: dict[str, str] | None = None,
    default_category_combine_op: str = "rss",
    post_processing_chain: list[dict[str, Any]] | None = None,
    scalars: dict[str, Any] | None = None,
) -> BudgetNode:
    """Build a hierarchical budget tree from tabular terms and explicit chain config.

    By default, expected table columns are CBE, Allocation, and Type. Additional
    columns are optional metadata copied into ``BudgetNode.metadata``.

    Use ``field_map`` (or ``config['field_map']``) to map these generic concepts
    to budget-specific column names. Field-map precedence is:
    defaults < inferred adapter mapping < ``config['field_map']`` < ``field_map``.
    """
    if isinstance(budget_or_table, BudgetNode):
        return budget_or_table

    records, derived_config, adapter_field_map = _resolve_table_and_config(budget_or_table, config)
    chain = (
        post_processing_chain
        if post_processing_chain is not None
        else derived_config.get("post_processing_chain")
    )
    if not chain:
        raise BudgetTreeError(_format_schema_error())

    effective_field_map = {"cbe": "CBE", "allocation": "Allocation", "type": "Type"}
    if adapter_field_map:
        effective_field_map.update(adapter_field_map)
    config_field_map = derived_config.get("field_map")
    if isinstance(config_field_map, dict):
        effective_field_map.update(config_field_map)
    if field_map:
        effective_field_map.update(field_map)

    required_field_keys = ("cbe", "allocation", "type")
    for key in required_field_keys:
        if key not in effective_field_map or not effective_field_map[key]:
            raise BudgetTreeError(f"Missing required field_map entry '{key}'.")

    for key in required_field_keys:
        column = effective_field_map[key]
        if not records or column not in records[0]:
            raise BudgetTreeError(f"Missing required table column '{column}' mapped from '{key}'.")

    grouped: dict[str, list[BudgetNode]] = {}
    cbe_column = effective_field_map["cbe"]
    allocation_column = effective_field_map["allocation"]
    type_column = effective_field_map["type"]
    for record in records:
        node = BudgetNode(
            name=_leaf_name(record),
            value=float(record[cbe_column]) if record[cbe_column] is not None else None,
            allocation=float(record[allocation_column]) if record[allocation_column] is not None else None,
            kind="leaf",
            metadata=dict(record),
        )
        type_value = str(record.get(type_column, "Uncategorized"))
        grouped.setdefault(type_value, []).append(node)

    category_nodes: list[BudgetNode] = []
    category_combine_ops = category_combine_ops or derived_config.get("category_combine_ops", {})
    for type_value, leaves in grouped.items():
        combine_op = category_combine_ops.get(type_value, default_category_combine_op)
        category = BudgetNode(
            name=f"{type_value} (subtotal)",
            value=None,
            allocation=None,
            kind="category",
            combine_op=combine_op,
            op_label=_build_op_label(combine_op, {"Type": type_value}, None),
            metadata={"Type": type_value},
            children=leaves,
        )
        category.value, category.allocation = _compute_node_value(category)
        category_nodes.append(category)

    current: BudgetNode | None = None
    for index, step in enumerate(chain):
        if "op" not in step:
            raise BudgetTreeError("Each post_processing_chain step must define 'op'.")
        op = step["op"]
        if op not in _COMBINE_OPS:
            raise BudgetTreeError(f"Unsupported combine_op '{op}' in post_processing_chain.")

        step_metadata = dict(step)
        if index == 0:
            children: list[BudgetNode] = list(category_nodes)
        else:
            if current is None:
                raise BudgetTreeError("post_processing_chain is invalid: missing prior rollup node.")
            children = [current]

        if op == "scalar_multiply":
            if current is None:
                raise BudgetTreeError("scalar_multiply cannot be the first post_processing_chain step.")
            factor = _resolve_factor(step, derived_config, scalars)
            step_metadata["factor"] = factor
            scalar_node = BudgetNode(
                name=step.get("factor_label", f"× {factor:g}"),
                value=factor,
                allocation=None,
                kind="scalar",
                metadata={"Type": "scalar"},
            )
            children = [scalar_node, current]

        node = BudgetNode(
            name=step.get("label", op),
            value=None,
            allocation=None,
            kind="rollup",
            combine_op=op,
            op_label=_build_op_label(op, step_metadata, step.get("op_label")),
            metadata={"Type": step.get("type", "rollup"), **step_metadata},
            children=children,
        )
        node.value, node.allocation = _compute_node_value(node)
        current = node

    if current is None:
        raise BudgetTreeError("post_processing_chain cannot be empty.")
    return current


def _format_number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1e}"


def _ascii_value(node: BudgetNode, show: str) -> str:
    if show == "cbe":
        return _format_number(node.value)
    if show == "allocation":
        return _format_number(node.allocation)
    return _format_number(node.value)


def _ascii_alloc_suffix(node: BudgetNode, show: str) -> str:
    if show == "both" and node.allocation is not None:
        return f" ({_format_number(node.allocation)} alloc)"
    return ""


def render_ascii(node: BudgetNode, show: str = "both") -> str:
    """Render a budget tree as an ASCII hierarchy."""
    if show not in {"both", "cbe", "allocation"}:
        raise BudgetTreeError("show must be one of: both, cbe, allocation")

    lines: list[str] = []

    def walk(
        current: BudgetNode,
        prefix: str,
        is_last: bool,
        edge_label: str | None,
        depth: int,
    ) -> None:
        connector = ""
        child_prefix = prefix
        if depth > 0:
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

        display_name = current.name
        if edge_label:
            display_name = f"{edge_label} {display_name}"
        value_text = _ascii_value(current, show)
        suffix = _ascii_alloc_suffix(current, show)
        lines.append(f"{prefix}{connector}{display_name} ... {value_text}{suffix}")
        for child_index, child in enumerate(current.children):
            walk(
                child,
                child_prefix,
                child_index == len(current.children) - 1,
                current.op_label if current.children else None,
                depth + 1,
            )

    walk(node, "", True, None, 0)
    return "\n".join(lines)


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _latex_text(text: str) -> str:
    if _contains_latex(text):
        return text
    return _latex_escape(text)


def _contains_latex(text: str) -> bool:
    return "$" in text or "\\" in text


def _escape_preserving_latex(text: str) -> str:
    escaped: list[str] = []
    for char in text:
        if char in ("\\", "$"):
            escaped.append(char)
        else:
            escaped.append(_latex_escape(char))
    return "".join(escaped)


def _collect_types(node: BudgetNode) -> list[str]:
    types: list[str] = []

    def walk(current: BudgetNode) -> None:
        type_value = str(current.metadata.get("Type", current.kind))
        if type_value not in types:
            types.append(type_value)
        for child in current.children:
            walk(child)

    walk(node)
    return types


def _style_name(type_name: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "_" for char in type_name).strip("_")
    return f"type_{safe or 'unknown'}"


def _is_over_allocated(node: BudgetNode) -> bool:
    is_leaf = node.kind == "leaf"
    has_values = node.value is not None and node.allocation is not None
    exceeds_allocation = has_values and node.value > node.allocation
    return is_leaf and exceeds_allocation


def _node_label(node: BudgetNode, show: str) -> str:
    warning_prefix = r"$\triangle!$ " if _is_over_allocated(node) else ""
    lines = [warning_prefix + str(node.name)]
    if show in ("both", "cbe"):
        lines.append(f"CBE: {_format_number(node.value)}")
    if show in ("both", "allocation") and node.allocation is not None:
        lines.append(f"alloc: {_format_number(node.allocation)}")
    table_lines = []
    for line in lines:
        if _contains_latex(line):
            table_lines.append(_escape_preserving_latex(line))
        else:
            table_lines.append(_latex_escape(line))
    return r"\begin{tabular}{l}" + r" \\\\ ".join(table_lines) + r"\end{tabular}"


def _render_forest_node(node: BudgetNode, show: str, parent_op_label: str | None = None) -> str:
    type_name = str(node.metadata.get("Type", node.kind))
    options = [f"draw", f"rounded corners", f"align=left", _style_name(type_name)]
    if _is_over_allocated(node):
        options.append("overallocated")
    if parent_op_label:
        options.append(f"edge label={{node[midway,left,font=\\scriptsize]{{{_latex_text(parent_op_label)}}}}}")

    children = "".join(_render_forest_node(child, show, node.op_label) for child in node.children)
    return f"[{_node_label(node, show)}, {', '.join(options)}{children}]"


def render_tikz(node: BudgetNode, show: str = "both", standalone: bool = True) -> str:
    """Render a budget tree to tikz/forest LaTeX."""
    if show not in {"both", "cbe", "allocation"}:
        raise BudgetTreeError("show must be one of: both, cbe, allocation")

    palette = [
        "blue!15",
        "green!15",
        "orange!20",
        "purple!15",
        "teal!15",
        "gray!20",
        "cyan!15",
    ]
    type_styles = []
    for index, type_name in enumerate(_collect_types(node)):
        color = palette[index % len(palette)]
        type_styles.append(f"{_style_name(type_name)}/.style={{fill={color}}}")

    style_block = "\n".join(type_styles + ["overallocated/.style={draw=red, very thick, font=\\bfseries}"])
    forest = (
        "\\tikzset{\n"
        f"{style_block}\n"
        "}\n"
        "\\begin{forest}\n"
        "for tree={grow'=south, s sep=8mm, l sep=10mm}\n"
        f"{_render_forest_node(node, show)}\n"
        "\\end{forest}\n"
    )

    if not standalone:
        return forest

    return (
        "\\documentclass[tikz,border=5pt]{standalone}\n"
        "\\usepackage{forest}\n"
        "\\begin{document}\n"
        f"{forest}"
        "\\end{document}\n"
    )


def compile_to_pdf(tex_path: str | Path) -> Path:
    """Compile a tex file to PDF with pdflatex."""
    tex_path = Path(tex_path)
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        raise BudgetTreeError("pdflatex binary not found. Install LaTeX to compile tikz output.")
    command = [pdflatex, "-interaction=nonstopmode", tex_path.name]
    proc = subprocess.run(command, cwd=tex_path.parent, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise BudgetTreeError(f"pdflatex failed for {tex_path.name}:\n{proc.stderr or proc.stdout}")
    return tex_path.with_suffix(".pdf")


def display_tree(
    budget_or_node: Any,
    *,
    show: str = "both",
    standalone: bool = True,
    config: dict[str, Any] | None = None,
    field_map: dict[str, str] | None = None,
    post_processing_chain: list[dict[str, Any]] | None = None,
    scalars: dict[str, Any] | None = None,
) -> Any:
    """Display tree output in IPython, with best-effort PDF compile."""
    node = budget_or_node if isinstance(budget_or_node, BudgetNode) else build_tree(
        budget_or_node,
        config=config,
        field_map=field_map,
        post_processing_chain=post_processing_chain,
        scalars=scalars,
    )
    tex = render_tikz(node, show=show, standalone=standalone)

    try:
        from IPython.display import Code, IFrame, display
    except Exception:
        return tex

    temp_dir = Path(tempfile.mkdtemp(prefix="budgie_tree_"))
    tex_path = temp_dir.joinpath("budget_tree.tex")
    tex_path.write_text(tex, encoding="utf-8")
    try:
        pdf_path = compile_to_pdf(tex_path)
        display(IFrame(src=str(pdf_path), width=900, height=700))
        return pdf_path
    except BudgetTreeError:
        display(Code(tex, language="latex"))
        return tex

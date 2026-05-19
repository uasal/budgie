"""Build and render hierarchical budget trees.

This module takes a *flat* table of budget terms and turns it into a nested
:class:`BudgetNode` tree that is easier to inspect in plain text and LaTeX.
Each input row becomes a leaf, leaves are grouped by their ``Type`` column into
category subtotal nodes, and those category nodes are then wrapped by an
explicit post-processing "spine" such as ``rss -> scalar_multiply ->
scalar_multiply``.

There are therefore three conceptual layers in the final tree:

1. leaf terms copied directly from the input table,
2. category subtotal nodes created from the leaf ``Type`` groups, and
3. post-processing nodes created from ``post_processing_chain``.

The *math* for each combine operation lives in the ``_COMBINE_OPS`` registry in
this file. The YAML/config only chooses *which* registered operation to use for
category nodes (via ``category_combine_ops``) and for post-processing nodes
(via ``post_processing_chain``); it does not define arbitrary formulas.

The required budget concepts are generic: CBE, Allocation, and Type. Their
actual table column names are resolved in this order: an explicit ``field_map``
keyword argument wins, then ``config["field_map"]``, then an adapter-detected
legacy mapping for budget-like objects, and finally the default
``{"cbe": "CBE", "allocation": "Allocation", "type": "Type"}`` map.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Callable


class BudgetTreeError(Exception):
    """Error raised when tree construction, rendering, or PDF compilation fails.

    Callers see this exception when the input table is missing required columns,
    when the post-processing chain is malformed, when an unknown combine
    operator is requested, or when external LaTeX compilation fails.
    """


@dataclass
class BudgetNode:
    """One node in the hierarchical budget tree.

    The dataclass decorator asks Python to generate the repetitive ``__init__``,
    ``__repr__``, and comparison helpers for us, so the model can be described
    mostly by its fields.

    Parameters
    ----------
    name:
        Human-readable label shown in ASCII and tikz output.
    value:
        The node's current best estimate (CBE). Leaf values come directly from
        the input table. Non-leaf values are computed from the node's children
        by the node's ``combine_op``.
    allocation:
        The allocated budget for the node. Leaf allocations come directly from
        the input table. Non-leaf allocations are computed from the children by
        the same ``combine_op`` used for the value.
    kind:
        Structural role of the node, such as ``leaf``, ``category``, ``rollup``,
        or ``scalar``.
    combine_op:
        Name of the registered operation used to combine child values for
        non-leaf nodes. Leaves leave this as ``None``.
    op_label:
        LaTeX/text label displayed on the incoming edge to each child, such as
        ``RSS`` or ``$\\times g_{pp}$``.
    metadata:
        Extra source-table fields or configuration fields carried alongside the
        node for rendering and debugging.
    children:
        Child nodes. Leaves have an empty list.
    """

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
    """Registry entry describing one combine operation.

    This tiny dataclass is the registry payload: ``func`` performs the math,
    while ``label_builder`` supplies the default edge label used by the
    renderers when a config step does not override it.
    """

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


# ``_COMBINE_OPS`` is the central extension registry for tree math.
# Built-in operators are listed here so readers can see both their semantics and
# their default edge labels without chasing each function definition:
#   - rss: sqrt(sum(c_i^2))                  -> $\sqrt{\sum c_i^2}$
#   - sum: sum(c_i)                         -> $\sum$
#   - product: product(c_i)                 -> $\prod$
#   - scalar_multiply: c * factor           -> $\times {factor}$
#   - max: max(c_i)                         -> $\max$
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
    """Register a new combine operation.

    This is the public extension point for adding new tree math. The YAML/config
    can only *select* from names in this registry, so new combine behavior must
    be registered in Python code first and then referenced by name.
    """
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
    """Normalize supported table-like inputs into a list of dictionaries."""
    if hasattr(table, "reset_index") and hasattr(table, "to_dict"):
        return table.reset_index().to_dict("records")
    if isinstance(table, list):
        return [dict(record) for record in table]
    raise BudgetTreeError("Unsupported table type. Provide a pandas-like table or list of records.")


def _resolve_table_and_config(
    budget_or_table: Any,
    config: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str] | None]:
    """Resolve an input object into records, config, and any inferred field map.

    The ``hasattr(..., "get_pandas_table")`` check is duck typing: instead of
    requiring a specific class, we accept any object that behaves like a budget
    adapter by exposing the method we need.
    """
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
            # This legacy map keeps older budget-like adapters working when they
            # still expose prefixed ``<domain> CBE`` / ``<domain> Allocation``
            # column pairs instead of the generic names.
            if inferred_cbe and inferred_allocation and "Type" in columns:
                adapter_field_map = {"cbe": inferred_cbe, "allocation": inferred_allocation, "type": "Type"}
        return records, derived_config, adapter_field_map

    return _coerce_table_records(budget_or_table), derived_config, adapter_field_map


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
    """Return the best available display name from common source-table columns."""
    for key in ("Name", "name", "Term", "term", "index", "Item", "item", "Description"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return "leaf"


def _compute_node_value(node: BudgetNode) -> tuple[float | None, float | None]:
    """Compute aggregate value/allocation for a non-leaf node."""
    if not node.children or not node.combine_op:
        return node.value, node.allocation
    if node.combine_op not in _COMBINE_OPS:
        raise BudgetTreeError(f"Unsupported combine_op '{node.combine_op}'.")

    spec = _COMBINE_OPS[node.combine_op]

    value_children = [child.value for child in node.children if child.value is not None]
    alloc_children = [child.allocation for child in node.children if child.allocation is not None]
    factor = node.metadata.get("factor")

    if node.combine_op == "scalar_multiply":
        # Scalar-multiply nodes carry an extra scalar child so the tree shows the
        # factor explicitly, but the math should only multiply the non-scalar
        # budget child.
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
    """Build a hierarchical budget tree from tabular terms and explicit config.

    Parameters are intentionally layered so callers can override pieces of a
    YAML/config object at runtime. ``field_map`` is resolved in this order:
    explicit keyword argument, then ``config['field_map']``, then any
    adapter-detected legacy mapping, and finally the default generic map.

    ``post_processing_chain`` follows the same explicit-over-config rule. The
    chain must be provided explicitly either by keyword argument or inside the
    config; there is no implicit default because the post-processing spine is a
    modeling choice that should be visible to the caller.
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
        if not records:
            raise BudgetTreeError(f"Missing required table column '{column}' mapped from '{key}'.")
        for row_index, record in enumerate(records):
            if column not in record:
                raise BudgetTreeError(
                    f"Missing required table column '{column}' mapped from '{key}' in row index {row_index}."
                )

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
    """Return the budget tree as a plain-text ASCII hierarchy.

    The function only returns a string; it does not write files or invoke any
    external tools. This renderer intentionally stays simple and does not try to
    mirror the visual alert styling used by the tikz renderers.
    """
    if show not in {"both", "cbe", "allocation"}:
        raise BudgetTreeError("show must be one of: both, cbe, allocation")

    lines: list[str] = []

    # ``walk`` is a nested recursive helper: it calls itself for each child so
    # the same small block of logic can handle trees of any depth.
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


def _contains_latex(text: str) -> bool:
    return "$" in text or "\\" in text


def _latex_text(text: str) -> str:
    if _contains_latex(text):
        return text
    return _latex_escape(text)


def _collect_types(node: BudgetNode) -> list[str]:
    """Collect unique ``Type`` values so each one can receive a tikz style."""
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
    raw = "".join(char.lower() if char.isalnum() else "_" for char in type_name)
    safe = "_".join(part for part in raw.split("_") if part)
    return f"type_{safe or 'unknown'}"


def _is_over_allocated(node: BudgetNode) -> bool:
    is_leaf = node.kind == "leaf"
    has_values = node.value is not None and node.allocation is not None
    exceeds_allocation = has_values and node.value > node.allocation
    return is_leaf and exceeds_allocation


def _meets_allocation(node: BudgetNode) -> bool:
    is_leaf = node.kind == "leaf"
    has_values = node.value is not None and node.allocation is not None
    within_allocation = has_values and node.value <= node.allocation
    return is_leaf and within_allocation


def _format_leaf_value_text(node: BudgetNode, value_text: str, alert_on_exceedances: bool) -> str:
    r"""Format the displayed CBE value for a leaf node.

    ``\underline{...}`` gives positive feedback for leaves that meet their
    allocation. ``\colorbox{yellow!50}{...}`` is a yellow background highlight
    used only for over-allocated leaves, and only when alerts are enabled.
    """
    escaped_value = _latex_escape(value_text)
    if _meets_allocation(node):
        return rf"\underline{{{escaped_value}}}"
    if alert_on_exceedances and _is_over_allocated(node):
        return rf"\colorbox{{yellow!50}}{{{escaped_value}}}"
    return escaped_value


def _styled_node_name(node: BudgetNode, alert_on_exceedances: bool) -> str:
    warning_prefix = r"$\triangle!$ " if alert_on_exceedances and _is_over_allocated(node) else ""
    return f"{warning_prefix}{_latex_text(str(node.name))}"


def _node_label_forest(node: BudgetNode, show: str, alert_on_exceedances: bool) -> str:
    """Build the multi-line label used inside a forest node box."""
    lines = [_styled_node_name(node, alert_on_exceedances)]
    if show in ("both", "cbe"):
        value_text = _format_leaf_value_text(node, _format_number(node.value), alert_on_exceedances)
        lines.append(f"{_latex_escape('CBE: ')}{value_text}")
    if show in ("both", "allocation") and node.allocation is not None:
        lines.append(f"{_latex_escape('alloc: ')}{_latex_escape(_format_number(node.allocation))}")

    # ``tabular`` gives the forest node controlled line breaks. Using the ``c``
    # column type centers each line inside the box instead of left-justifying it.
    return r"\begin{tabular}{c}" + r" \\\\ ".join(lines) + r"\end{tabular}"


def _outline_value_text(node: BudgetNode, show: str, alert_on_exceedances: bool) -> str:
    if show == "allocation":
        return _latex_escape(_format_number(node.allocation))

    parts = []
    if show in ("both", "cbe"):
        parts.append(_format_leaf_value_text(node, _format_number(node.value), alert_on_exceedances))
    if show == "both" and node.allocation is not None:
        parts.append(f"{_latex_escape('(alloc ')}{_latex_escape(_format_number(node.allocation))}{_latex_escape(')')}")
    return " ".join(parts) if parts else _latex_escape(_format_number(node.value))


def _node_label_outline(node: BudgetNode, show: str, alert_on_exceedances: bool) -> str:
    """Build the single-line label used by the directory-style outline layout."""
    name_text = _styled_node_name(node, alert_on_exceedances)
    value_text = _outline_value_text(node, show, alert_on_exceedances)
    if value_text:
        # ``\dotfill`` inserts stretchy dotted leaders between the label and the
        # value so the number visually lines up on the right.
        return f"{name_text} \\dotfill {value_text}"
    return name_text


def _render_forest_node(
    node: BudgetNode,
    show: str,
    alert_on_exceedances: bool,
    parent_op_label: str | None = None,
) -> str:
    """Recursively render one node and its descendants in ``forest`` syntax."""
    type_name = str(node.metadata.get("Type", node.kind))
    options = ["draw", "rounded corners", "align=center", _style_name(type_name)]
    if alert_on_exceedances and _is_over_allocated(node):
        options.append("overallocated")
    if parent_op_label:
        options.append(f"edge label={{node[midway,left,font=\\scriptsize]{{{_latex_text(parent_op_label)}}}}}")

    # The forest renderer is recursive: each node returns a string that embeds
    # the rendered strings of its children, so one function handles the entire
    # tree regardless of depth.
    children = "".join(_render_forest_node(child, show, alert_on_exceedances, node.op_label) for child in node.children)
    return f"[{_node_label_forest(node, show, alert_on_exceedances)}, {', '.join(options)}{children}]"


def _render_outline_node(
    node: BudgetNode,
    show: str,
    alert_on_exceedances: bool,
    *,
    depth: int = 0,
) -> str:
    """Recursively render one node and its descendants in tikz tree syntax."""
    indent = "  " * depth
    type_name = str(node.metadata.get("Type", node.kind))
    options = ["draw", "rounded corners", "align=left", "anchor=west", _style_name(type_name)]
    if alert_on_exceedances and _is_over_allocated(node):
        options.append("overallocated")

    parts = [f"{indent}node[{', '.join(options)}]{{{_node_label_outline(node, show, alert_on_exceedances)}}}"]
    for child in node.children:
        edge_label = ""
        if node.op_label:
            edge_label = (
                " edge from parent node[midway,above right,font=\\scriptsize,text=gray]"
                f"{{{_latex_text(node.op_label)}}}"
            )
        parts.append(
            "\n"
            f"{indent}  child {{\n"
            f"{_render_outline_node(child, show, alert_on_exceedances, depth=depth + 2)}"
            f"{edge_label}\n"
            f"{indent}  }}"
        )
    return "".join(parts)


def _tikz_style_block(node: BudgetNode, alert_on_exceedances: bool) -> str:
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

    # ``\tikzset{...}`` defines reusable named styles. We auto-generate one fill
    # style per ``Type`` so new categories pick up palette colors automatically.
    if alert_on_exceedances:
        type_styles.append("overallocated/.style={draw=red, very thick, font=\\bfseries}")
    return "\\tikzset{\n" + "\n".join(type_styles) + "\n}\n"


def render_tikz(
    node: BudgetNode,
    *,
    show: str = "both",
    standalone: bool = True,
    layout: str = "forest",
    alert_on_exceedances: bool = True,
) -> str:
    """Return tikz LaTeX for the tree.

    Parameters
    ----------
    node:
        The already-built tree to render.
    show:
        Which numeric fields to show: ``both``, ``cbe``, or ``allocation``.
    standalone:
        When ``True`` the return value is a complete LaTeX document that can be
        compiled directly. When ``False`` only the tikz/forest fragment is
        returned so callers can embed it into a larger document.
    layout:
        ``forest`` produces boxed nodes in a top-down tree. ``outline`` produces
        a directory-style outline similar to the example discussed at
        https://latexdraw.com/draw-trees-in-tikz/.
    alert_on_exceedances:
        When ``True`` (the default), over-allocated leaves get the existing
        warning prefix, yellow highlight, and red border. When ``False``, those
        negative alert cues are suppressed while the underline for leaves that
        meet their allocation remains visible.

    Returns
    -------
    str
        LaTeX source code only; this function does not write files or invoke
        external programs.
    """
    if show not in {"both", "cbe", "allocation"}:
        raise BudgetTreeError("show must be one of: both, cbe, allocation")
    if layout not in {"forest", "outline"}:
        raise BudgetTreeError("layout must be one of: forest, outline")

    style_block = _tikz_style_block(node, alert_on_exceedances)
    if layout == "forest":
        forest = (
            style_block
            # ``forest`` is a LaTeX package specialized for tree diagrams. The
            # ``for tree={...}`` block supplies default options applied to every
            # node in the environment.
            + "\\begin{forest}\n"
            + "for tree={grow'=south, s sep=8mm, l sep=10mm}\n"
            + f"{_render_forest_node(node, show, alert_on_exceedances)}\n"
            + "\\end{forest}\n"
        )
        body = forest
    else:
        outline = (
            style_block
            # ``tikzpicture`` is the generic drawing environment used for the
            # outline layout. The grow/edge options below follow the directory
            # tree pattern from latexdraw.com.
            + "\\begin{tikzpicture}[\n"
            # ``grow via three points`` tells tikz where to place the first and
            # later children so the tree reads like an indented outline rather
            # than a centered org chart.
            + "grow via three points={one child at (0,-0.9) and two children at (0,-0.9) and (10em,-0.9)},\n"
            # In tikz path syntax, ``|-`` means "go vertically, then turn and go
            # horizontally". That creates the elbow-style connector seen in many
            # directory trees.
            + "edge from parent path={(\\tikzparentnode.south) |- (\\tikzchildnode.west)},\n"
            + "every node/.style={font=\\small},\n"
            + "]\n"
            + f"{_render_outline_node(node, show, alert_on_exceedances)};\n"
            + "\\end{tikzpicture}\n"
        )
        body = outline

    if not standalone:
        return body

    # The ``standalone`` document class is convenient for one-off renders: it
    # produces a tightly-cropped PDF that can be embedded into reports without
    # needing to manually trim page margins.
    return (
        "\\documentclass[tikz,border=5pt]{standalone}\n"
        "\\usepackage{forest}\n"
        "\\usepackage{xcolor}\n"
        "\\begin{document}\n"
        f"{body}"
        "\\end{document}\n"
    )


def compile_to_pdf(tex_path: str | Path) -> Path:
    """Compile a ``.tex`` file to PDF with ``pdflatex``.

    The input ``.tex`` file is expected to exist already. This function runs the
    external ``pdflatex`` command, writes the usual LaTeX side-product files in
    the same directory, and returns the path to the generated PDF.
    """
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
    layout: str = "forest",
    alert_on_exceedances: bool = True,
    config: dict[str, Any] | None = None,
    field_map: dict[str, str] | None = None,
    post_processing_chain: list[dict[str, Any]] | None = None,
    scalars: dict[str, Any] | None = None,
) -> Any:
    """Display a tree in IPython and return the rendered artifact.

    If ``budget_or_node`` is not already a :class:`BudgetNode`, the function
    first calls :func:`build_tree`. It then calls :func:`render_tikz`, writes the
    LaTeX to a temporary directory, and makes a best effort to compile and
    display a PDF inline in IPython. When IPython or ``pdflatex`` is unavailable,
    it falls back to returning/displaying the raw LaTeX string instead.
    """
    node = budget_or_node if isinstance(budget_or_node, BudgetNode) else build_tree(
        budget_or_node,
        config=config,
        field_map=field_map,
        post_processing_chain=post_processing_chain,
        scalars=scalars,
    )
    tex = render_tikz(
        node,
        show=show,
        standalone=standalone,
        layout=layout,
        alert_on_exceedances=alert_on_exceedances,
    )

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

from pathlib import Path
from unittest import TestCase

import pandas as pd

from budgie.tree import BudgetTreeError, build_tree, register_combine_op, render_ascii, render_tikz


FIXTURES_DIR = Path(__file__).parent.joinpath("fixtures")


def _sample_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Name": "coherent_1",
                "Allocation": 4.0e-9,
                "CBE": 3.0e-9,
                "Type": "Static, Coherent",
                "Description": "first coherent term",
                "CBE Trace": "trace-a",
            },
            {
                "Name": "coherent_2",
                "Allocation": 4.0e-9,
                "CBE": 4.0e-9,
                "Type": "Static, Coherent",
                "Description": "second coherent term",
                "CBE Trace": "trace-b",
            },
            {
                "Name": "incoherent_1",
                "Allocation": 0.5e-9,
                "CBE": 1.0e-9,
                "Type": "Static, Incoherent",
                "Description": "incoherent term",
                "CBE Trace": "trace-c",
            },
            {
                "Name": "dynamic_1",
                "Allocation": 2.0e-9,
                "CBE": 2.0e-9,
                "Type": "Dynamic",
                "Description": "dynamic term",
                "CBE Trace": "trace-d",
            },
        ]
    )


def _sample_config() -> dict:
    return {
        "pp_gain": 0.1,
        "post_processing_chain": [
            {"op": "rss", "label": "Total raw value", "op_label": "RSS"},
            {
                "op": "scalar_multiply",
                "factor_key": "pp_gain",
                "label": "Post-processed value",
                "op_label": r"$\times g_{pp}$",
            },
            {"op": "scalar_multiply", "factor": 5, "label": "5σ Post-processed value", "op_label": "5×"},
        ],
    }


def _count_edge_labels(node) -> int:
    parent_edge_count = len(node.children) if node.op_label else 0
    child_edge_count = sum(_count_edge_labels(child) for child in node.children)
    return parent_edge_count + child_edge_count


class TestTreeRendering(TestCase):
    def test_ascii_snapshot(self):
        node = build_tree(_sample_table(), config=_sample_config())
        actual = render_ascii(node, show="both")
        expected = FIXTURES_DIR.joinpath("tree_ascii_snapshot.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(actual.strip(), expected)

    def test_tikz_structure_edge_labels_and_overallocation(self):
        node = build_tree(_sample_table(), config=_sample_config())
        tikz = render_tikz(node, show="both", standalone=False)

        self.assertIn("\\begin{forest}", tikz)
        self.assertIn("\\end{forest}", tikz)
        self.assertIn("overallocated", tikz)
        self.assertEqual(tikz.count("edge label={"), _count_edge_labels(node))

    def test_requires_post_processing_chain(self):
        with self.assertRaises(BudgetTreeError) as ctx:
            build_tree(_sample_table(), config={})
        self.assertIsInstance(ctx.exception, BudgetTreeError)
        message = str(ctx.exception)
        self.assertIn("post_processing_chain", message)
        self.assertIn("<combine_op>", message)
        self.assertNotIn("Total raw value", message)

    def test_new_type_auto_generates_style(self):
        table = _sample_table()
        table = pd.concat(
            [
                table,
                pd.DataFrame(
                    [
                        {
                            "Name": "new_type_leaf",
                            "Allocation": 1.0e-9,
                            "CBE": 0.8e-9,
                            "Type": "New Type",
                            "Description": "new type term",
                            "CBE Trace": "trace-z",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        node = build_tree(table, config=_sample_config())
        tikz = render_tikz(node, standalone=False)
        self.assertIn("type_new_type/.style", tikz)

    def test_field_map_supports_legacy_column_names(self):
        generic_node = build_tree(_sample_table(), config=_sample_config())
        legacy_table = _sample_table().rename(
            columns={"CBE": "Contrast CBE", "Allocation": "Contrast Allocation"}
        )
        mapped_node = build_tree(
            legacy_table,
            config=_sample_config(),
            field_map={"cbe": "Contrast CBE", "allocation": "Contrast Allocation", "type": "Type"},
        )
        self.assertEqual(render_ascii(mapped_node, show="both"), render_ascii(generic_node, show="both"))

    def test_adapter_auto_maps_suffix_cbe_allocation_columns(self):
        generic_node = build_tree(_sample_table(), config=_sample_config())
        legacy_table = _sample_table().rename(
            columns={"CBE": "Contrast CBE", "Allocation": "Contrast Allocation"}
        )

        class _LegacyBudgetLike:
            def __init__(self, table, config):
                self._table = table
                self.budget = config

            def get_pandas_table(self):
                return self._table

        mapped_node = build_tree(_LegacyBudgetLike(legacy_table, _sample_config()))
        self.assertEqual(render_ascii(mapped_node, show="both"), render_ascii(generic_node, show="both"))

    def test_field_map_from_config(self):
        generic_node = build_tree(_sample_table(), config=_sample_config())
        legacy_table = _sample_table().rename(
            columns={"CBE": "Contrast CBE", "Allocation": "Contrast Allocation"}
        )
        config = dict(_sample_config())
        config["field_map"] = {"cbe": "Contrast CBE", "allocation": "Contrast Allocation", "type": "Type"}
        mapped_node = build_tree(legacy_table, config=config)
        self.assertEqual(render_ascii(mapped_node, show="both"), render_ascii(generic_node, show="both"))

    def test_only_generic_required_columns(self):
        minimal_table = _sample_table()[["Name", "Allocation", "CBE", "Type"]]
        node = build_tree(minimal_table, config=_sample_config())
        self.assertIsNotNone(node.value)
        self.assertIsNotNone(node.allocation)

        def _find_first_leaf(current):
            if current.kind == "leaf":
                return current
            for child in current.children:
                leaf = _find_first_leaf(child)
                if leaf is not None:
                    return leaf
            return None

        leaf = _find_first_leaf(node)
        self.assertIsNotNone(leaf)
        self.assertNotIn("Description", leaf.metadata)
        self.assertNotIn("CBE Trace", leaf.metadata)

    def test_custom_combine_op_registration(self):
        def _range(values, **_):
            return max(values) - min(values)

        register_combine_op("range", _range, r"$\max-\min$")
        config = {
            "post_processing_chain": [
                {"op": "range", "label": "Range total"},
            ]
        }
        node = build_tree(_sample_table(), config=config, default_category_combine_op="sum")
        self.assertEqual(node.combine_op, "range")
        self.assertGreater(node.value, 0)

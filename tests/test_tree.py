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
                "Contrast Allocation": 4.0e-9,
                "Contrast CBE": 3.0e-9,
                "Type": "Static, Coherent",
                "Description": "first coherent term",
                "CBE Trace": "trace-a",
            },
            {
                "Name": "coherent_2",
                "Contrast Allocation": 4.0e-9,
                "Contrast CBE": 4.0e-9,
                "Type": "Static, Coherent",
                "Description": "second coherent term",
                "CBE Trace": "trace-b",
            },
            {
                "Name": "incoherent_1",
                "Contrast Allocation": 0.5e-9,
                "Contrast CBE": 1.0e-9,
                "Type": "Static, Incoherent",
                "Description": "incoherent term",
                "CBE Trace": "trace-c",
            },
            {
                "Name": "dynamic_1",
                "Contrast Allocation": 2.0e-9,
                "Contrast CBE": 2.0e-9,
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
            {"op": "rss", "label": "Total raw contrast", "op_label": "RSS"},
            {
                "op": "scalar_multiply",
                "factor_key": "pp_gain",
                "label": "Post-processed contrast",
                "op_label": r"$\times g_{pp}$",
            },
            {"op": "scalar_multiply", "factor": 5, "label": "5σ Post-processed contrast", "op_label": "5×"},
        ],
    }


def _count_edge_labels(node) -> int:
    count = len(node.children) if node.children and node.op_label else 0
    for child in node.children:
        count += _count_edge_labels(child)
    return count


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
        with self.assertRaises(BudgetTreeError):
            build_tree(_sample_table(), config={})

    def test_new_type_auto_generates_style(self):
        table = _sample_table()
        table.loc[len(table)] = {
            "Name": "new_type_leaf",
            "Contrast Allocation": 1.0e-9,
            "Contrast CBE": 0.8e-9,
            "Type": "New Type",
            "Description": "new type term",
            "CBE Trace": "trace-z",
        }
        node = build_tree(table, config=_sample_config())
        tikz = render_tikz(node, standalone=False)
        self.assertIn("type_new_type/.style", tikz)

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


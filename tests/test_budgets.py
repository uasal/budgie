import inspect
from pathlib import Path
from unittest import TestCase

import numpy as np

import budgets

TEST_SUPPORT_DATA_DIR = Path(__file__).parents[1].joinpath("tests", "data")


class TestBudgets(TestCase):
    "Tests for psd_utils."

    def test_calc_margins(self):
        """Tests."""

        filename = TEST_SUPPORT_DATA_DIR.joinpath("test_budget.yaml")
        print(f"{filename=}")
        test_bud = budgets.Budgets(filename, budget_dir=TEST_SUPPORT_DATA_DIR)
        margins = test_bud.calc_margins()

        # self.assertAlmostEqual(
        #     _expect, _got, places=7, msg=f"Expected {_expect}, but got {_got}"
        # )

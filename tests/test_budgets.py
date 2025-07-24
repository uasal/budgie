import inspect
from pathlib import Path
from unittest import TestCase

import numpy as np

from budgie import Budget, set_directory

# Sets the budget data path for looking up any budget yaml files and reports output directory.
set_directory(Path(__file__).parents[1].joinpath("tests", "data"))
output_dir = Path(__file__).parents[1].joinpath("reports")

class TestBudgets(TestCase):
    "Tests for psd_utils."

    def test_calc_margins(self):
        """Tests."""

        filename = "test_budget.yaml"
        test_bud = Budget(filename)
        margins = test_bud.calc_margins()

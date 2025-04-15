import inspect
from pathlib import Path
from unittest import TestCase
from budgie import set_directory

import numpy as np

from budgie import Budget

# Set the directory of the test data
set_directory(Path(__file__).parents[1].joinpath("tests/data"))

class TestBudgets(TestCase):
    "Tests for psd_utils."
        
    def test_calc_margins(self):
        """Tests."""

        filename = "test_budget.yaml"
        test_bud = Budget(filename)
        margins = test_bud.calc_margins()


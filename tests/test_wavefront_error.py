import inspect
import pprint
from pathlib import Path
from unittest import TestCase

import numpy as np

from budgie import WaveFrontError

TEST_SUPPORT_DATA_DIR = Path(__file__).parents[1].joinpath("tests", "data")


class TestWaveFrontError(TestCase):
    "Tests."

    def test_calc_total(self):
        """Tests."""

        filename = TEST_SUPPORT_DATA_DIR.joinpath("test_budget.yaml")

        # load the class
        wfe_class = WaveFrontError()

        total_cbe, total_spec, total_allocation = wfe_class.calc_total_wfe()


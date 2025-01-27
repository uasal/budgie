import inspect
import pprint
from pathlib import Path
from unittest import TestCase
import numpy as np
from budgets import WaveFrontError

TEST_SUPPORT_DATA_DIR = Path(__file__).parents[1].joinpath("tests", "data")


class TestWaveFrontError(TestCase):
    "Tests."

    def test_calc_total(self):
        """Tests."""

        filename = TEST_SUPPORT_DATA_DIR.joinpath("test_budget.yaml")

        # load the class
        # this test is dumb because it uses the real file
        wfe_class = WaveFrontError()
        total_cbe, total_spec, total_allocation = wfe_class.calc_total_wfe()
        # # expect -6 to 6 in pixels, but multiplied by dx
        # _expect = 1
        # _got = margins
        # self.assertEqual(_expect, _got, f"Expected {_expect}, but got {_got}")

        # # check maximimum radius is correct (in dx space)
        # _expect = np.sqrt(2) * (dims[0] // 2 * dx)
        # _got = np.max(coords.r_grid)


# path = "../budgets/wavefront_error/wavefront_error.yaml"
# with open(path, "r") as file:
#     iq = yaml.safe_load(file)

# # print(iq)

# pprint.pprint(iq)

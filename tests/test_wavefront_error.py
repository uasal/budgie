from pathlib import Path
from unittest import TestCase
from budgie import set_directory
import pytest


from budgie import WaveFrontError

# Set the directory of the test data
set_directory(Path(__file__).parents[1].joinpath("tests/data"))



def test_calc_total():
    """Tests."""

    filename = "test_budget.yaml"

    # load the class
    wfe_class = WaveFrontError(filename)

    total_cbe, total_spec, total_allocation = wfe_class.calc_total_wfe()

    print(f"{total_cbe=}")
    print(f"{total_spec=}")
    print(f"{total_allocation=}")
    assert total_cbe == pytest.approx(1.1660e-08)
    assert total_spec == pytest.approx(8.888194417315589e-09)
    assert total_allocation == pytest.approx(3.44093010681705e-08)


from pathlib import Path

import pytest

from budgie import DMStroke, set_directory

TEST_SUPPORT_DATA_DIR = Path(__file__).parents[1].joinpath("tests", "data")


@pytest.fixture
def dm():
    set_directory(TEST_SUPPORT_DATA_DIR)
    return DMStroke("test_dm_stroke.yaml")


def test_total_stroke_is_surface_deflection(dm):
    assert dm.total_stroke == pytest.approx(1400)


def test_group_margins_are_linear_sums(dm):
    static = dm.budget["static"]
    assert static["curr_spec"] == pytest.approx(400)
    assert static["curr_cbe"] == pytest.approx(372)
    assert static["margin_spec"] == pytest.approx(0.0)
    assert static["margin_cbe"] == pytest.approx(28)


def test_calc_total_stroke(dm):
    total_cbe, total_spec, total_allocation = dm.calc_total_stroke()
    assert total_allocation == pytest.approx(500)
    assert total_spec == pytest.approx(500)
    assert total_cbe == pytest.approx(457)
    assert dm.total_stroke - total_allocation == pytest.approx(900)


def test_run_report_writes_file(dm, tmp_path):
    dm.run_report(tmp_path)
    report = tmp_path.joinpath("dm-stroke-report.md").read_text()
    assert "Total DM Surface Stroke Available: 1400.0 [nm]" in report
    assert "Total Allocated Stroke: 500.0 [nm]" in report
    assert "Unallocated Stroke Reserve: 900.0 [nm]" in report
    assert "WARNING" not in report


def test_groups_can_mix_rss_and_sum(tmp_path):
    (tmp_path / "mixed.yaml").write_text(
        "dm:\n"
        "  surface_deflection: 1000\n"
        "random:\n"
        "  combine: rss\n"
        "  allocation: 100\n"
        "  a: {spec: 30, cbe: 30}\n"
        "  b: {spec: 40, cbe: 40}\n"
        "systematic:\n"
        "  allocation: 100\n"
        "  c: {spec: 30, cbe: 30}\n"
        "  d: {spec: 40, cbe: 40}\n",
        encoding="utf-8",
    )
    set_directory(tmp_path)
    dm = DMStroke("mixed.yaml")
    assert dm.budget["random"]["curr_spec"] == pytest.approx(50)
    assert dm.budget["systematic"]["curr_spec"] == pytest.approx(70)
    total_cbe, total_spec, _ = dm.calc_total_stroke()
    assert total_spec == pytest.approx(120)


def test_over_allocation_warns(tmp_path):
    (tmp_path / "over.yaml").write_text(
        "dm:\n"
        "  surface_deflection: 100\n"
        "group:\n"
        "  allocation: 150\n"
        "  a: {spec: 30, cbe: 30}\n",
        encoding="utf-8",
    )
    set_directory(tmp_path)
    DMStroke("over.yaml").run_report(tmp_path)
    assert "WARNING" in tmp_path.joinpath("dm-stroke-report.md").read_text()


def test_unknown_combine_raises(tmp_path):
    (tmp_path / "bad.yaml").write_text(
        "dm:\n"
        "  surface_deflection: 1000\n"
        "group:\n"
        "  combine: average\n"
        "  allocation: 100\n"
        "  a: {spec: 30, cbe: 30}\n",
        encoding="utf-8",
    )
    set_directory(tmp_path)
    with pytest.raises(ValueError):
        DMStroke("bad.yaml")

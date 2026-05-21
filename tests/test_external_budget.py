import importlib.util
from pathlib import Path

import pytest

from budgie import set_directory

_RUN_REPORT_PATH = Path(__file__).parents[1].joinpath("scripts", "run_report.py")
_SPEC = importlib.util.spec_from_file_location("run_report", _RUN_REPORT_PATH)
_RUN_REPORT = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_RUN_REPORT)
resolve_budget = _RUN_REPORT.resolve_budget


def test_resolve_and_execute_external_budget(tmp_path, monkeypatch):
    module_path = tmp_path / "tmp_module.py"
    module_path.write_text(
        "from budgie import Budget\n"
        "class DummyBudget(Budget):\n"
        "    def __init__(self, name):\n"
        "        super().__init__(name)\n"
        "        self.run_report_called = False\n"
        "    def run_report(self, output_dir):\n"
        "        self.run_report_called = True\n",
        encoding="utf-8",
    )
    (tmp_path / "fixture.yaml").write_text("allocation: 1\n", encoding="utf-8")

    monkeypatch.syspath_prepend(tmp_path)
    set_directory(tmp_path)

    budget = resolve_budget("tmp_module:DummyBudget", "fixture.yaml")

    assert budget.__class__.__name__ == "DummyBudget"
    assert budget.name == "fixture.yaml"
    budget.run_report(tmp_path)
    assert budget.run_report_called is True


def test_non_budget_external_class_raises_type_error(tmp_path, monkeypatch):
    module_path = tmp_path / "tmp_non_budget.py"
    module_path.write_text(
        "class NotABudget:\n"
        "    def __init__(self, *args, **kwargs):\n"
        "        pass\n",
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(tmp_path)

    with pytest.raises(TypeError):
        resolve_budget("tmp_non_budget:NotABudget", "fixture.yaml")


def test_unknown_builtin_yaml_with_yaml_name_raises_lookup_error():
    with pytest.raises(LookupError):
        resolve_budget("unknown_budget.yaml", "fixture.yaml")

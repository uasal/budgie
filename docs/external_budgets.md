# External Budgets

`budgie` can run `Budget` subclasses defined in other Python packages using the
`module:ClassName` form in `scripts/run_report.py`.

Usage:

```bash
python scripts/run_report.py package_name.module_path:BudgetClassName budget_input.yaml
```

Example:

```bash
python scripts/run_report.py stp_etc_imaging.budget_adapter:ExposureTimeBudget targets.yaml
```

# Budget Yaml Information

## General Info
If using the `test.sh` or `run_report.py`, put the source budget yaml files in this directory for it to run (if not using notebooks or other scripts).

## Structure Notes

### Calculating margins
For the calculate margins functionality to work, the values in the yaml data file sources need to follow the following:

  - Scientific notation needs to have a decimal point specified before the `e` 
  - Scientific notation needs to have a sign specified
    - The `+` is not implied naturally (at the moment)
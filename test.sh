# Testing / not finished.

# Argument Settings -------------------------------------------------
## Script Directory / File to run
SCRIPT="scripts/run_report.py"

## Budget yaml data file names
## ADJUST these file names to be what the budget yaml files actually are within the `data` directory that are to be used for the reports.
ML="mission_lifetime.yaml"
WFE="wavefront_error.yaml"
TR="transient_response.yaml"
TEST="test_budget.yaml"
PL="test_plantuml.yaml"

# Installing package (if not done already or modified)
pip install .

# Running Scripts  --------------------------------------------------
## Adjust this if you want only a specific file.
## Can you command-line input instead / this is more for testing
python "${SCRIPT}" "${ML}" "${WFE}" "${TR}"

# For using the gui interface instead for diagrams w/plantuml
#java -jar plantuml.jar -gui

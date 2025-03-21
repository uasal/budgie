import sys
from pathlib import Path
from budgets import *

# Test diagram temp section / demo
file_test = "tests/data/test_budget.yaml"
destination = "diagrams/test_plantuml.yaml"

# Sets the budget data path for looking up any budget yaml files and reports output directory.
set_directory(Path(__file__).parents[1].joinpath("data"))
output_dir = Path(__file__).parents[1].joinpath("reports")
print('Grabbing yaml file(s) for running report...')
print("Argument list collected: ", sys.argv)
args = 1


# Running reports
if __name__ == "__main__":
    print("Starting run_report script...")
    # Run throw all the positions of args collected and stop before it reaches the end.
    while args < len(sys.argv):
        budget_name = sys.argv[args]
        #print(f"{budget_name=}")
        # Determine budget subclass based on the name of file
        if budget_name == "wavefront_error.yaml":
            budget = WaveFrontError()
        elif budget_name == "mission_lifetime.yaml":
            budget = MissionLifetime()
        elif budget_name == "transient_response.yaml":
            budget = TransientResponse()
        else:
            raise LookupError(f"Cannot find {budget_name}")
        # Increment args
        args = args + 1
        # Perform calculations for budget(s) and generates an output markdown file with results.
        budget.run_report(output_dir)
        print("Budget Report Results printed to: " + str(output_dir))

    # Quick test / demo example for the plantuml diagram
    print("Creating plantuml file and generating diagram from yaml...")
    diagram = Plantuml_Writer.create_plantuml(file_test, destination)

    # Will give a message if no arguments were provided.
    if len(sys.argv) == 1:
        print("No args specified in command. Add the file name(s) after 'run_report.py' to specify the reports you want to run.")


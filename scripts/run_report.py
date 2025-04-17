import sys
from pathlib import Path
from budgie import set_directory, WaveFrontError, MissionLifetime, TransientResponse, Plantuml_Writer, ScatteredLight

# Test diagram temp section / demo
file_test = "tests/data/test_budget.yaml"
destination = "diagrams/test_plantuml.yaml"


# Running reports
if __name__ == "__main__":
    print("Starting run_report script...")
    # Run throw all the positions of args collected and stop before it reaches the end.
    args=1
    while args < len(sys.argv):
        budget_name = Path(sys.argv[args])

        # Set the appropriate data directory and output directory based on the input file
        # If no path data is given then it assumes the files are in the budgie repo
        if len(budget_name.parents) == 1:
            set_directory(Path(__file__).parents[1].joinpath("data"))
            output_dir = Path(__file__).parents[1].joinpath("reports")
        else:
            # Assume same structure (as in gitlab) but derive from path
            set_directory(Path(budget_name).parents[1].joinpath("data"))
            output_dir = Path(budget_name).parents[1].joinpath("reports")

        # Determine budget subclass based on the name of file
        if "wavefront_error.yaml" in str(budget_name).lower():
            budget = WaveFrontError(budget_name)
        elif "mission_lifetime.yaml" in str(budget_name).lower():
            budget = MissionLifetime(budget_name)
        elif "transient_response.yaml" in str(budget_name).lower():
            budget = TransientResponse(budget_name)
        elif "scattered" in str(budget_name).lower():
            budget = ScatteredLight(budget_name)
        else:
            raise LookupError(f"Cannot find a budget that is associable with {budget_name}")
        # Increment args
        args = args + 1
        # Perform calculations for budget(s) and generates an output markdown file with results.
        budget.run_report(output_dir)
        print("Budget Report Results printed to: " + str(output_dir))

    # Quick test / demo example for the plantuml diagram
    print("Creating plantuml file and generating diagram from yaml...")
    diagram = Plantuml_Writer.create_plantuml(budget_name, output_dir)

    # Will give a message if no arguments were provided.
    if len(sys.argv) == 1:
        print("No args specified in command. Add the file name(s) after 'run_report.py' to specify the reports you want to run.")


import importlib
import sys
from pathlib import Path
from budgie import (
    Budget,
    MissionLifetime,
    Plantuml_Writer,
    TransientResponse,
    WaveFrontError,
    set_directory,
)


# Test diagram temp section / demo
file_test = "tests/data/test_budget.yaml"
destination = "diagrams/test_plantuml.yaml"

# Sets the budget data path for looking up any budget yaml files and reports output directory.
set_directory(Path(__file__).parents[1].joinpath("data"))
output_dir = Path(__file__).parents[1].joinpath("reports")
print('Grabbing yaml file(s) for running report...')
print("Argument list collected: ", sys.argv)
args = 1


def is_external_budget_spec(spec):
    # CLI contract: built-in budgets are simple yaml/toml names while plug-ins
    # use "module:ClassName". Keep this check aligned with the issue requirement.
    return ":" in spec and not spec.endswith((".yaml", ".toml"))


def resolve_budget(spec, yaml_name=None):
    if is_external_budget_spec(spec):
        module_path, class_name = spec.split(":", 1)
        budget_class = getattr(importlib.import_module(module_path), class_name)
        if not isinstance(budget_class, type) or not issubclass(budget_class, Budget):
            raise TypeError(
                f"{module_path}:{class_name} must resolve to a subclass of budgie.Budget"
            )
        if yaml_name is None:
            raise ValueError(
                f"External budget '{module_path}:{class_name}' requires a YAML filename argument"
            )
        return budget_class(yaml_name)

    if spec == "wavefront_error.yaml":
        return WaveFrontError()
    if spec == "mission_lifetime.yaml":
        return MissionLifetime()
    if spec == "transient_response.yaml":
        return TransientResponse()
    raise LookupError(f"Cannot find {spec}")


# Running reports
if __name__ == "__main__":
    print("Starting run_report script...")
    # Run throw all the positions of args collected and stop before it reaches the end.
    while args < len(sys.argv):
        budget_spec = sys.argv[args]
        yaml_name = None
        if is_external_budget_spec(budget_spec):
            if args + 1 >= len(sys.argv):
                raise ValueError(
                    f"External budget '{budget_spec}' requires a YAML filename argument"
                )
            yaml_name = sys.argv[args + 1]
            args += 1

        budget = resolve_budget(budget_spec, yaml_name)
        # Increment args
        args += 1
        # Perform calculations for budget(s) and generates an output markdown file with results.
        budget.run_report(output_dir)
        print("Budget Report Results printed to: " + str(output_dir))

    # Quick test / demo example for the plantuml diagram
    print("Creating plantuml file and generating diagram from yaml...")
    diagram = Plantuml_Writer.create_plantuml(file_test, destination)

    # Will give a message if no arguments were provided.
    if len(sys.argv) == 1:
        print("No args specified in command. Add the file name(s) after 'run_report.py' to specify the reports you want to run.")

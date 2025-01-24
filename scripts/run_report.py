import sys

import budgets
import mission_lifetime
import transient_response
import wavefront_error  # this is a bad way to do this, want it to be as below

# from budgets import wavefront_error

print("argument list", sys.argv)
budget_name = sys.argv[1]
print(f"{budget_name=}")

if __name__ == "__main__":
    print("starting script")

    # import the wfe class
    if budget_name == "wavefront_error.yaml":
        budget = wavefront_error.WaveFrontError()
    elif budget_name == "mission_lifetime.yaml":
        budget = mission_lifetime.MissionLifetime()
    elif budget_name == "transient_response.yaml":
        budget = transient_response.TransientResponse()
    else:
        raise LookupError(f"Cannot find {budget_name}")

    # Calculate and report the total WFE.
    budget.run_report()

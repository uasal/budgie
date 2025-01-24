# This is a file that is where user puts any math that needs to be done with their budget.
# it contains standard functions which are called via scripts (e.g. run_report)

import inspect
from pathlib import Path
from pprint import pprint

import numpy as np

import budgets
import mission_lifetime
from budgets import find_vals

BUDGET_DATA_DIR = Path(__file__).parents[2].joinpath("budgets")
NAME = "transient_response.yaml"


class TransientResponse:
    def __init__(self):
        print("initialized TransientResponse class")
        self.tr = budgets.Budgets(NAME)

        # Calculate target acquisition
        # First Read in mission lifetime budget to get transient slew times.
        ml = mission_lifetime.MissionLifetime()
        prep_payload = ml.large_slew + ml.large_acq_lock + ml.guide_wfs
        print(f"{prep_payload/60=:0.1f} [min]")

        # Now add that term to the budget
        # FIXME: The proper way to do this is to have cbes and specs
        # slew = {"curr_spec": prep_payload, "curr_cbe": prep_payload}

        self.tr.budget["spacecraft_operations"]["slew_and_prep"]["spec"] = prep_payload
        self.tr.budget["spacecraft_operations"]["slew_and_prep"]["cbe"] = prep_payload

        self.tr.calc_margins(rss=False)  # don't use rss to add values

    def calc_total_time(self):
        """Calculates totals of CBE, allocation, and spec."""

        # Use recursion to go infinitely deep and get each curr_cbe, curr_spec, and allocation

        vals = list(find_vals(self.tr.budget, "curr_spec"))
        # now add the values the list.
        total_spec = np.sum(vals)

        vals = list(find_vals(self.tr.budget, "curr_cbe"))
        total_cbe = np.sum(vals)

        vals = list(find_vals(self.tr.budget, "allocation"))
        total_allocation = np.sum(vals)

        return total_cbe, total_spec, total_allocation

    def run_report(self):
        # Method that is called by a generic script
        # needs to be in every budget class.

        total_cbe, total_spec, total_allocation = self.calc_total_time()
        pprint(self.tr.budget)

        print(f"Total CBE Time [min]: {total_cbe/60:0.2f} [min]")
        print(f"Total Specified Time: {total_spec/60:0.2f} [min]")
        print(f"Total Allocated Time: {total_allocation/60:0.2f} [min]")

        print(
            f"Total Margin against Specified Time: {(total_allocation-total_spec)/60:0.2f} [min]"
        )
        print(
            f"Total Margin against CBE Time: {(total_allocation-total_cbe)/60:0.2f} [min]"
        )

# This is a file that is where user puts any math that needs to be done with their budget.
# it contains standard functions which are called via scripts (e.g. run_report)

import inspect
from pathlib import Path
import pprint

import numpy as np

from budgie.core import Budget, MissionLifetime, find_vals
from budgie.version import __version__

#BUDGET_DATA_DIR = Path(__file__).parents[2].joinpath("data")
NAME = "transient_response.yaml"
YAML_LOC = f"../data/{NAME}"


class TransientResponse(Budget):

    def __init__(self):
        print("initialized TransientResponse class")
        super(Budget, self).__init__()
        self.tr = Budget(NAME)
        self.tr.calc_margins()

        # Calculate target acquisition
        # First Read in mission lifetime budget to get transient slew times.
        ml = MissionLifetime()
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

    def run_report(self, output_dir):
        """ Runs report for budget and outputs to the specified directory.
        :param output_dir: string to output directory path
        """
        # Method that is called by a generic script
        # needs to be in every budget class.
        print("Running Transient Response Report...")
        report_title = "# Transient Response Report\n\n"
        data_header = "## Transient Response Results\n\n"
        version = f"**Version:** _{__version__}_\n\n" 
        total_cbe, total_spec, total_allocation = self.calc_total_time()
        yaml = pprint.pformat(self.tr.budget)
        yaml_data = f"## [Transient Response Yaml]({YAML_LOC})\n\n```yaml\n {yaml} \n```\n"
        path = output_dir.joinpath("tr-report.md")
        end = "\n"

        total_cbe_time = f"- Total CBE Time [min]: {total_cbe/60:0.2f} [min]\n"
        total_specified_time = f"- Total Specified Time: {total_spec/60:0.2f} [min]\n"
        total_allocated_time = f"- Total Allocated Time: {total_allocation/60:0.2f} [min]\n"
        total_margin_specified = f"- Total Margin against Specified Time: {(total_allocation-total_spec)/60:0.2f} [min]\n"
        total_margin_cbe = f"- Total Margin against CBE Time: {(total_allocation-total_cbe)/60:0.2f} [min]\n"
        data = total_cbe_time + total_specified_time + total_allocated_time + total_margin_specified + total_margin_cbe + "\n"

        print(data)
        report = report_title + version + data_header + data + yaml_data

        with open(path, "w+", encoding="utf-8", newline=end) as f:
            f.write(report)

        print("Transient Response Budget Report completed.")



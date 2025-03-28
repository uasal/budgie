# This is a file that is where user puts any math that needs to be done with their budget.
# it contains standard functions which are called via scripts (e.g. run_report)

from pathlib import Path
from pprint import pprint
import math

import numpy as np
import pprint

from budgets.core import Budget, find_vals
from budgets.version import __version__

#BUDGET_DATA_DIR = Path(__file__).parents[2].joinpath("data")
NAME = "wavefront_error.yaml"
YAML_LOC = f"../data/{NAME}"


class WaveFrontError(Budget):

    def __init__(self):
        print("initialized WaveFrontError class")
        # instantiate the budget class
        super(Budget, self).__init__()
        self.wfe = Budget(NAME)
        self.wfe.calc_margins()

    def calc_total_wfe(self):
        """Calculates totals of CBE, allocation, and spec"""

        # Use recursion to go infinitely deep and get each curr_cbe, curr_spec, and allocation

        # tmp = list(find_vals(self.wfe.budget, "allocation"))
        # print(f"allocation {[round(i * 1e9) for i in tmp]=}")

        vals = list(find_vals(self.wfe.budget, "curr_spec"))
        # now RSS the list.
        total_spec = np.sqrt(np.sum(i * i for i in vals))

        vals = list(find_vals(self.wfe.budget, "curr_cbe"))
        total_cbe = np.sqrt(np.sum(i * i for i in vals))

        vals = list(find_vals(self.wfe.budget, "allocation"))
        total_allocation = np.sqrt(np.sum(i * i for i in vals))

        return total_cbe, total_spec, total_allocation

    def run_report(self, output_dir):
        """ Runs report for budget and outputs to the specified directory.
        :param output_dir: string to output directory path
        """
        # Method that is called by a generic script
        # needs to be in every budget class.
        path = output_dir.joinpath("wfe-report.md")
        report_title = "# Wavefront Error Report\n\n"
        yaml = pprint.pformat(self.wfe.budget)
        report_budget = f"## [WFE Yaml Reference]({YAML_LOC})\n\n```yaml\n {yaml} \n```\n"
        version = f"**Version:** _{__version__}_\n\n" 
        report_results = "## WFE Report Results\n\n"
        end = "\n"
        total_cbe, total_spec, total_allocation = self.calc_total_wfe()

        #wavefront error for a Strehl of 0.8
        # s= exp( -(2*pi*w)^2), where w is the RMS WFE in waves.
        # sqrt(-ln s) / (2*pi)) = w 
        s08_wfe = math.sqrt(-math.log(0.8))/(2*math.pi) # in waves
        total_rms_wfe = f"- Total RMS WFE for a Strehl of 0.8 at 1um is: {s08_wfe*1000:0.2f} [nm]\n"
        total_cbe_wfe = f"- Total CBE WFE: {total_cbe*1e9:0.2f} [nm] \n"
        total_spec_wfe = f"- Total Specified WFE: {total_spec*1e9:0.2f} [nm] \n"
        total_allocation_wfe = f"- Total Allocated WFE: {total_allocation*1e9:0.2f} [nm]\n"
        total_margin_spec_wfe = f"- Total Margin against Specified WFE: {(total_allocation-total_spec)*1e9:0.2f} [nm]\n"
        total_margin_cbe_wfe = f"- Total Margin against CBE WFE: {(total_allocation-total_cbe)*1e9:0.2f} [nm]\n"
        report = report_title + version + report_results + total_rms_wfe + total_cbe_wfe + total_spec_wfe + total_allocation_wfe + total_margin_spec_wfe + total_margin_cbe_wfe + end + report_budget
        print(report)

        with open(path, "w+", encoding="utf-8", newline=end) as f:
            f.write(report)

        print("Report Results Generated. Verify to the reports directory markdown file for the report results.")
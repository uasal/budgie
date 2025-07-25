# This is a file that is where user puts any math that needs to be done with their budget.
# it contains standard functions which are called via scripts (e.g. run_report)

from pathlib import Path
from pprint import pprint
import math

import numpy as np
import yaml

from budgie.core import Budget, find_vals
from budgie.version import __version__

NAME = "wavefront_error.yaml"
YAML_LOC = f"../data/{NAME}"


class WaveFrontError(Budget):

    def __init__(self, name):
        print("initialized WaveFrontError class")
        # instantiate the budget class
        super(Budget, self).__init__()
        self.wfe = Budget(name)
        self.wfe.calc_margins()

    def calc_total_wfe(self):
        """Calculates totals of CBE, allocation, and spec"""

        # Use recursion to go infinitely deep and get each curr_cbe, curr_spec, and allocation

        vals = list(find_vals(self.wfe.budget, "curr_spec"))
        # now RSS the list.
        # total_spec = np.sqrt(np.sum(i * i for i in vals)) # deprecated behavior

        # create a generator to modernize
        gen = (i**2 for i in vals)
        total_spec = np.sqrt(np.sum(np.fromiter(gen,dtype=float)))

        vals = list(find_vals(self.wfe.budget, "curr_cbe"))
        gen = (i**2 for i in vals)
        total_cbe = np.sqrt(np.sum(np.fromiter(gen,dtype=float)))

        vals = list(find_vals(self.wfe.budget, "allocation"))
        gen = (i**2 for i in vals)
        total_allocation = np.sqrt(np.sum(np.fromiter(gen,dtype=float)))

        return float(total_cbe), float(total_spec), float(total_allocation)

    def run_report(self, output_dir):
        """ Runs report for budget and outputs to the specified directory.
        :param output_dir: string to output directory path
        """
        # Method that is called by a generic script
        # needs to be in every budget class.
        path = output_dir.joinpath("wfe-report.md")
        report_title = "# Wavefront Error Report\n\n"
        yaml_out = yaml.safe_dump(self.wfe.budget) 
        report_budget = f"## [WFE Yaml Reference]({YAML_LOC})\n\n```yaml\n {yaml_out} \n```\n"
        version = f"**Version:** _{__version__}_\n\n" 
        report_results = "## WFE Report Results\n\n"
        end = "\n"
        total_cbe, total_spec, total_allocation = self.calc_total_wfe()

        #wavefront error for a Strehl of 0.8
        # s= exp( -(2*pi*w)^2), where w is the RMS WFE in waves.
        # sqrt(-ln s) / (2*pi)) = w 
        strehl=self.wfe.budget['strehl_spec'] 
        strehl_wfe_waves = math.sqrt(-math.log(strehl))/(2*math.pi) # in waves
        
        design_wavelength = self.wfe.budget['design_wavelength']  # [nm]
        total_rms_wfe = f"- Total RMS WFE for a Strehl of 0.8 at {design_wavelength:0.1f} [nm] is: {strehl_wfe_waves*design_wavelength:0.2f} [nm]\n"
        total_cbe_wfe = f"- Total CBE WFE: {total_cbe*1e9:0.2f} [nm] \n"
        total_spec_wfe = f"- Total Specified WFE: {total_spec*1e9:0.2f} [nm] \n"
        total_allocation_wfe = f"- Total Allocated WFE: {total_allocation*1e9:0.2f} [nm]\n"
        total_margin_spec_wfe = f"- Total Margin against Specified WFE: {(total_allocation-total_spec)*1e9:0.2f} [nm]\n"
        total_margin_cbe_wfe = f"- Total Margin against CBE WFE: {(total_allocation-total_cbe)*1e9:0.2f} [nm]\n"
        report = report_title + version + report_results + total_rms_wfe + total_cbe_wfe + total_spec_wfe + total_allocation_wfe + total_margin_spec_wfe + total_margin_cbe_wfe + end + report_budget
        short_report = report_title + version + total_rms_wfe + total_cbe_wfe + total_spec_wfe + total_allocation_wfe + total_margin_spec_wfe + total_margin_cbe_wfe + end 
        print(short_report)

        with open(path, "w+", encoding="utf-8", newline=end) as f:
            f.write(report)

        # Also write out the budget results only
        # Write YAML to a file
        yaml_path = output_dir.joinpath("wfe-report.yaml")
        with open(yaml_path, 'w') as file:
            yaml.safe_dump(self.wfe.budget, file, default_flow_style=False, indent=4)


        print("Report Results Generated. Verify to the reports directory markdown file for the report results.")
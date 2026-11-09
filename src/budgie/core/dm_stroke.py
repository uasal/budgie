# This is a file that is where user puts any math that needs to be done with their budget.
# it contains standard functions which are called via scripts (e.g. run_report)

import pprint

import numpy as np

from budgie.core import Budget, find_vals
from budgie.version import __version__

NAME = "dm_stroke.yaml"
YAML_LOC = f"../data/{NAME}"


class DMStroke(Budget):
    """Tracks and allocates deformable mirror stroke (surface peak-to-valley, in nm).

    Terms within an allocation are summed linearly rather than RSS'd, since stroke
    demands from different terms can stack on the same actuator.
    """

    def __init__(self, name=NAME):
        print("initialized DMStroke class")
        super().__init__(name)
        self.calc_margins(rss=False)
        self.total_stroke = self.budget["dm"]["surface_deflection"]

    def calc_total_stroke(self):
        """Calculates totals of CBE, spec, and allocation by summing each allocation group."""
        total_spec = np.sum(list(find_vals(self.budget, "curr_spec")))
        total_cbe = np.sum(list(find_vals(self.budget, "curr_cbe")))
        total_allocation = np.sum(list(find_vals(self.budget, "allocation")))

        return total_cbe, total_spec, total_allocation

    def run_report(self, output_dir):
        """ Runs report for budget and outputs to the specified directory.
        :param output_dir: string to output directory path
        """
        # Method that is called by a generic script
        # needs to be in every budget class.
        print("Running DM Stroke Report...")
        path = output_dir.joinpath("dm-stroke-report.md")
        report_title = "# Deformable Mirror Stroke Report\n\n"
        version = f"**Version:** _{__version__}_\n\n"
        report_results = "## DM Stroke Report Results\n\n"
        yaml = pprint.pformat(self.budget)
        report_budget = f"## [DM Stroke Yaml Reference]({YAML_LOC})\n\n```yaml\n {yaml} \n```\n"
        end = "\n"
        total_cbe, total_spec, total_allocation = self.calc_total_stroke()

        # Reported in nm of surface PV stroke
        data = (
            f"- Total DM Surface Stroke Available: {self.total_stroke:0.1f} [nm]\n"
            f"- Total Allocated Stroke: {total_allocation:0.1f} [nm]\n"
            f"- Unallocated Stroke Reserve: {(self.total_stroke-total_allocation):0.1f} [nm]\n"
            f"- Total Specified Stroke: {total_spec:0.1f} [nm]\n"
            f"- Total CBE Stroke: {total_cbe:0.1f} [nm]\n"
            f"- Total Margin against Specified Stroke: {(total_allocation-total_spec):0.1f} [nm]\n"
            f"- Total Margin against CBE Stroke: {(total_allocation-total_cbe):0.1f} [nm]\n"
        )
        if total_allocation > self.total_stroke:
            data += "- **WARNING:** Allocations exceed the available DM stroke.\n"

        report = report_title + version + report_results + data + end + report_budget
        print(report)

        with open(path, "w+", encoding="utf-8", newline=end) as f:
            f.write(report)

        print("DM Stroke Budget Report completed.")

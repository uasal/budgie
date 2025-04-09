# This is a file that is where user puts any math that needs to be done with their budget.
# it contains standard functions which are called via scripts (e.g. run_report)

import inspect
import sys
from pathlib import Path
from budgie.core import Budget, find_vals
import pprint
import numpy as np
from budgie.version import __version__

NAME = "mission_lifetime.yaml"
YAML_LOC = f"../data/{NAME}"

class MissionLifetime(Budget):

    def __init__(self):
        print("initialized MissionLifetime class")
        # instantiate the budget class
        super(Budget, self).__init__()
        self.ml = Budget(NAME)
        self.ml.calc_margins()

        # small slew and settle
        self.small_slew = self.ml.budget["spacecraft"]["short_slew"]["cbe"] + np.min(
            [
                self.ml.budget["payload"]["settling_foa"]["cbe"],
                self.ml.budget["payload"]["settling_aoa"]["cbe"],
            ]
        )
        # transient slew and settle
        self.large_slew = self.ml.budget["spacecraft"]["trans_slew"]["cbe"] + np.min(
            [
                self.ml.budget["payload"]["settling_foa"]["cbe"],
                self.ml.budget["payload"]["settling_aoa"]["cbe"],
            ]
        )
        # small acquire and lock
        self.acq_lock = (
            self.ml.budget["spacecraft"]["offset"]["cbe"]
            + self.ml.budget["control_sys"]["acq"]["exptime"]
            + self.ml.budget["control_sys"]["acq"]["wcs_calc"]
            + self.ml.budget["control_sys"]["acq"]["offset_calc"]
        ) * self.ml.budget["control_sys"]["acq"]["n_iter"]
        # large acquire and lock- FIXME: Add rough acquisition
        self.large_acq_lock = 2 * self.acq_lock
        L3_8002 = (
            self.ml.budget["control_sys"]["acq"]["exptime"]
            + self.ml.budget["control_sys"]["acq"]["wcs_calc"]
            + self.ml.budget["control_sys"]["acq"]["offset_calc"]
        )
        print(f"L3-8002 cbe value is {L3_8002:0.1f} [s]")
        # guide and minimize WFE
        self.guide_wfs = (
            self.ml.budget["control_sys"]["guide"]["setup"]
            + self.ml.budget["control_sys"]["wfs"]["setup"]
        )
        # sne/ifs standard visit open shutter time
        self.sne_shutter_time = (
            self.ml.budget["visits"]["std_visit_sne"]["exptime"]
            + self.ml.budget["visits"]["std_visit_sne"]["rdtime"]
            + self.ml.budget["visits"]["std_visit_sne"]["overhead"]
        ) * self.ml.budget["visits"]["std_visit_sne"]["n_exp"]
        # transient standard visit open shutter time
        self.trans_shutter_time = (
            self.ml.budget["visits"]["std_visit_trans"]["exptime"]
            + self.ml.budget["visits"]["std_visit_trans"]["rdtime"]
            + self.ml.budget["visits"]["std_visit_trans"]["overhead"]
        ) * self.ml.budget["visits"]["std_visit_trans"]["n_exp"]
        # uvs standard visit open shutter time
        self.uvs_shutter_time = (
            self.ml.budget["visits"]["std_visit_uvs"]["exptime"]
            + self.ml.budget["visits"]["std_visit_uvs"]["rdtime"]
            + self.ml.budget["visits"]["std_visit_uvs"]["overhead"]
        ) * self.ml.budget["visits"]["std_visit_uvs"]["n_exp"]
        # wcc standard visit open shutter time
        self.wcc_shutter_time = (
            self.ml.budget["visits"]["std_visit_wcc"]["exptime"]
            + self.ml.budget["visits"]["std_visit_wcc"]["rdtime"]
            + self.ml.budget["visits"]["std_visit_wcc"]["overhead"]
        ) * self.ml.budget["visits"]["std_visit_wcc"]["n_exp"]
        # esc standard visit open shutter time
        self.esc_shutter_time = (
            self.ml.budget["visits"]["std_visit_esc"]["exptime"]
            + self.ml.budget["visits"]["std_visit_esc"]["rdtime"]
            + self.ml.budget["visits"]["std_visit_esc"]["overhead"]
        ) * (
            self.ml.budget["visits"]["std_visit_esc"]["n_exp"]
            * self.ml.budget["visits"]["std_visit_esc"]["n_rolls"]
            * self.ml.budget["visits"]["std_visit_esc"]["n_dh"]
        )

    def calc_sci_case(self, visits, shutter_time, slew="small"):
        """Calculates total time per science case, except the ESC. The ESC uses calc_esc_case"""

        if slew == "large":
            slew = self.large_slew
            acq_lock = self.large_acq_lock
        elif slew == "small":
            slew = self.small_slew
            acq_lock = self.acq_lock
        else:
            raise OSError("slew must be 'small' or 'large'")

        tot = visits * (slew + acq_lock + self.guide_wfs + shutter_time)

        return tot

    def calc_esc_case(self, visits, shutter_time):
        """Calculates total time spent on ESC science"""

        # Calculate slew time per visit. Original slew is large, but offset to reference star is small.
        slew_time = (self.large_slew + self.large_acq_lock + self.guide_wfs) + (
            self.ml.budget["visits"]["std_visit_esc"]["n_slews"] - 1
        ) * (self.ml.budget["visits"]["std_visit_esc"]["n_rolls"]) * (
            self.small_slew + self.acq_lock + self.guide_wfs
        )

        # Calculate time closing ESC loops per visit
        setup_time = (
            (self.ml.budget["visits"]["std_visit_esc"]["n_slews"])
            * (self.ml.budget["visits"]["std_visit_esc"]["n_rolls"])
            * (
                self.ml.budget["visits"]["std_visit_esc"]["dh_setup_time"]
                + self.ml.budget["visits"]["std_visit_esc"]["setup_time"]
            )
        )

        tot = visits * (slew_time + setup_time + self.esc_shutter_time)

        return tot

    def calc_total_time(self):
        sne_tot = self.calc_sci_case(
            self.ml.budget["visits"]["n_sne"], self.sne_shutter_time
        )
        print(f'Total time doing SNe (IFS) science: {sne_tot/3.154e+7:0.2f} [yrs]")')

        trans_tot = self.calc_sci_case(
            self.ml.budget["visits"]["n_trans"], self.trans_shutter_time, slew="large"
        )
        print(
            f'Total time doing transit (UVS/IFS) science: {trans_tot/3.154e+7:0.2f} [yrs]")'
        )

        uvs_tot = self.calc_sci_case(
            self.ml.budget["visits"]["n_uvs"], self.uvs_shutter_time
        )
        print(f'Total time doing UVS science: {uvs_tot/3.154e+7:0.2f} [yrs]")')

        wcc_tot = self.calc_sci_case(
            self.ml.budget["visits"]["n_wcc"], self.wcc_shutter_time
        )
        print(f'Total time doing WCC science: {wcc_tot/3.154e+7:0.2f} [yrs]")')

        esc_tot = self.calc_esc_case(
            self.ml.budget["visits"]["n_esc"], self.esc_shutter_time
        )
        print(f'Total time doing ESC science: {esc_tot/3.154e+7:0.2f} [yrs]")')

        comm_tot = self.ml.budget["commissioning"]["allocation"]
        print(f'Total time doing commissioning: {comm_tot/3.154e+7:0.2f} [yrs]")')

        downtime = self.ml.budget["lifetime"] * (1 - self.ml.budget["uptime"])
        print(f'Estimated downtime: {downtime/3.154e+7:0.2f} [yrs]")')

        return sne_tot + trans_tot + uvs_tot + wcc_tot + esc_tot + comm_tot + downtime

    def run_report(self, output_dir):
        """ Runs report for budget and outputs to the specified directory. 
        :param output_dir: string to output directory path
        """
        # Method that is called by a generic script
        # needs to be in every budget class.
        print("Running report method for mission lifetime...")
        yaml = pprint.pformat(self.ml.budget)
        path = output_dir.joinpath("ml-report.md")
        report_title = "# Mission Lifetime Report\n\n"
        end = "\n"
        version = f"**Version:** _{__version__}_\n\n" 
        total = self.calc_total_time()
        margin = self.ml.budget["lifetime"] - total
        total_allocation = f"- Total Allocated Time: {total / 3.154e+7:0.2f} [yrs]\n"
        total_margin = f"- Current Margin: {margin / 3.154e+7:0.2f} [yrs]\n"
        report_yaml = f"## [Mission Lifetime Yaml Reference]({YAML_LOC})\n\n```yaml\n {yaml} \n```\n"
        report_results = f"## Mission Lifetime Report Results\n\n {total_allocation} {total_margin}\n"
        report = report_title + version + report_results + report_yaml

        print(f"Mission Lifetime YAML:\n {yaml}\n")
        print(report_results)

        with open(path, "w+", encoding="utf-8", newline=end) as f:
            f.write(report)

        print("Mission Lifetime Budget Report completed.")

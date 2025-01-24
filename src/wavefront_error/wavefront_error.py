# This is a file that is where user puts any math that needs to be done with their budget.
# it contains standard functions which are called via scripts (e.g. run_report)

import inspect
from pathlib import Path
from pprint import pprint
import math

import numpy as np

import budgets
from budgets import find_vals

BUDGET_DATA_DIR = Path(__file__).parents[2].joinpath("budgets")
NAME = "wavefront_error.yaml"


class WaveFrontError:
    def __init__(self):
        print("initialized WaveFrontError class")
        # instantiate the budget class
        self.wfe = budgets.Budgets(NAME)
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

    def run_report(self):
        # Method that is called by a generic script
        # needs to be in every budget class.

        total_cbe, total_spec, total_allocation = self.calc_total_wfe()
        pprint(self.wfe.budget)

        #wavefront error for a Strehl of 0.8
        # s= exp( -(2*pi*w)^2), where w is the RMS WFE in waves.
        # sqrt(-ln s) / (2*pi)) = w 
        s08_wfe=math.sqrt(-math.log(0.8))/(2*math.pi) # in waves

        print(f"Total RMS WFE for a Strehl of 0.8 at 1um is: {s08_wfe*1000:0.2f} [nm]")
        print(f"Total CBE WFE: {total_cbe*1e9:0.2f} [nm]")
        print(f"Total Specified WFE: {total_spec*1e9:0.2f} [nm]")
        print(f"Total Allocated WFE: {total_allocation*1e9:0.2f} [nm]")

        print(
            f"Total Margin against Specified WFE: {(total_allocation-total_spec)*1e9:0.2f} [nm]"
        )
        print(
            f"Total Margin against CBE WFE: {(total_allocation-total_cbe)*1e9:0.2f} [nm]"
        )



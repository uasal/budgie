# This is a file that is where user puts any math that needs to be done with their budget.
# it contains standard functions which are called via scripts (e.g. run_report)

import inspect
from pathlib import Path
import os
import matplotlib.pyplot as plt

from budgie.core import Budget, find_vals
import pprint
import numpy as np
from budgie.version import __version__
import pandas as pd
import sys


# Is there a more pythonic way to do this?
try:
    import config_stp
except ImportError:
    config_stp = None
try:
    import config_um
except ImportError:
    config_um = None

if config_stp == None and config_um == None:
    raise ImportError("Cannot import config_stp nor config_um packages")

# NAME = "scattered_light.yaml"
# YAML_LOC = f"../data/{NAME}"

import logging
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(lineno)s - %(levelname)s - %(message)s')
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)
logger.setLevel("DEBUG") 


class ScatteredLight():
    def __init__(self,budget_name):
        logger.debug("Initialized ScatteredLight class")
        super(Budget, self).__init__()

        self.scattered = Budget(budget_name)


    def plot_pst(theta, pst, title, color, label):
        plt.figure(figsize=(8, 5))
        plt.plot(theta, pst, marker='o', linestyle='-', color=color, label=label)
        plt.yscale('log')
        plt.xlabel(r"$\theta$ (degrees)")
        plt.ylabel("PST")
        plt.title(title)
        plt.legend()
        plt.grid(True, which="both", linestyle="--")
        plt.show(block=False)

    def calc_plate_scale(self):
        """Calculates the plate scale"""

    def calc_fov(self):

        # WCC FoV - FIXME: Verify it's the same as in Zemax
        x_fov = (
            0.115 * 2
        )  # [degrees] The field of view of the telescope in x as a float. This is from the whitepaper.
        y_fov = (
            0.043 * 2
        )  # The field of view of the telescope in y as a float. This is from the whitepaper.
        fov = (x_fov) * (y_fov) * (np.pi / 180) ** 2 * (206265) ** 2  # in [arcsec^2]
        fov_m2= 400e-3*155e-3 # From SPIE paper 

        print(f"FoV is: {x_fov*60:0.2f} by {y_fov*60:0.2f} [arcminutes]")
        print(f"FoV is: {fov/3600:0.2f} [arcmin^2]")
        print(f"FoV is: {x_fov*y_fov:0.2f} [deg^2]")

        return fov

    def calc_throughput(self):
        """Calculates throughput of the telescope."""

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

        # Read in PST data (theta and power in y and x dims)

        # create plots of PST(s) -- relative irradiance - 

        # Normalize to be 1 at the center of the field

        # Convert to Watts/m^2/arcsec for a 0th magnitude star

        # Scale to magnitude Xth incident star

        # Calculate surface flux in zodi's and compare to requirement
        # Note requirement should be something like X% coverage above a surface magnitude of X zodi's.

        # calculate in a surface magnitude

        # Determine coverage for an Xth magnitude star with a radius of R


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


# # Load Excel data
# dir = "/Users/pingraham/repos/gitlab/budgets/src/scattered_light"
# filename="lazuli_pst.xlsx"
# pst_file = Path(dir).joinpath(filename)
# # # pst_file = "lazuli_pst_no_scatter.xlsx"
# filename_ns= "lazuli_pst_no_scatter.xlsx"
# pst_file_ns = Path(dir).joinpath(filename_ns)

# df_y = pd.read_excel(pst_file, sheet_name=0)  # First sheet (Y-axis PST)
# df_y_ns = pd.read_excel(pst_file_ns, sheet_name=0)  # No scatter model (Y-axis)

# df_x = pd.read_excel(pst_file, sheet_name="x_pst")  # X-axis PST
# df_x_ns = pd.read_excel(pst_file_ns, sheet_name="x_pst")  # No scatter model (X-axis)

# # Extract data function
# def extract_data(df, start, end, col):
#     data = df.iloc[start:end, col].reset_index(drop=True)  # Reset index for alignment
#     return data


# # Function for safe normalization that fully avoids division by zero
# def safe_normalize(pst, pst_ns):
#     pst = pst.to_numpy()
#     pst_ns = pst_ns.to_numpy()

#     # Ensure both arrays have the same length
#     min_length = min(len(pst), len(pst_ns))
#     pst = pst[:min_length]
#     pst_ns = pst_ns[:min_length]

#     # Initialize with original values instead of zeros
#     pst_norm = pst.copy()
    
#     # Where ns values are nonzero, apply normalization
#     nonzero_mask = pst_ns != 0
#     pst_norm[nonzero_mask] = pst[nonzero_mask] / pst_ns[nonzero_mask]

#     return pd.Series(pst_norm)  # Convert back to Pandas Series for plotting



# # Y-axis data
# theta_y_full = extract_data(df_y, 2, 237, 0)
# pst_y_full = extract_data(df_y, 2, 237, 3)

# # Y-axis no-scatter data
# pst_y_full_ns = extract_data(df_y_ns, 2, 237, 3)

# # X-axis data
# theta_x_full = extract_data(df_x, 2, 225, 0)
# pst_x_full = extract_data(df_x, 2, 225, 3)

# # X-axis no-scatter data
# pst_x_full_ns = extract_data(df_x_ns, 2, 225, 3)


# # Normalize safely (if ns = 0, use original)
# pst_y_full_norm = safe_normalize(pst_y_full, pst_y_full_ns)

# pst_x_full_norm = safe_normalize(pst_x_full, pst_x_full_ns)

# # Function to plot data
# def plot_pst(theta, pst, title, color, label):
#     plt.figure(figsize=(8, 5))
#     plt.plot(theta, pst, marker='o', linestyle='-', color=color, label=label)
#     plt.yscale('log')
#     plt.xlabel(r"$\theta$ (degrees)")
#     plt.ylabel("PST")
#     plt.title(title)
#     plt.legend()
#     plt.grid(True, which="both", linestyle="--")
#     plt.show(block=False)

# # Plot raw PST Y data
# plot_pst(theta_y_full, pst_y_full, r"PST for $\theta_y$ (Full Field)", 'b', "PST Y Full Range")

# # Plot normalized PST Y data
# plot_pst(theta_y_full, pst_y_full_norm, r"Normalized PST for $\theta_y$ (Full Field)", 'r', "Normalized PST Y Full Range")

# # Plot raw PST X data
# plot_pst(theta_x_full, pst_x_full, r"PST for $\theta_x$ (Full Field)", 'b', "PST X Full Range")


# # theta_x_full, pst_x_full_norm = match_lengths(theta_x_full, pst_x_full_norm)


# # Plot normalized PST X data
# plot_pst(theta_x_full, pst_x_full_norm, r"Normalized PST for $\theta_x$ (Full Field)", 'r', "Normalized PST X Full Range")


# plt.show()

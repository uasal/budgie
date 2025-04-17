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
import utils_config
import pytest


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
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - L%(lineno)s - %(levelname)s - %(message)s"
)
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)
logger.setLevel("DEBUG")


class ScatteredLight(Budget):
    def __init__(self, budget_input_file):
        logger.debug("Initialized ScatteredLight class")
        super(Budget, self).__init__()
        self.budget_input_file = budget_input_file
        self.scattered = Budget(budget_input_file)

        if self.scattered.budget["project"] == "um":
            conf_project = config_um
        elif self.scattered.budget["project"] == "stp":
            conf_project = config_um
        else:
            raise ValueError(
                f"The budget project tag of {self.scattered.budget["project"]} must be set to 'um' or 'stp'."
            )

        config = conf_project.load_config_values()
        conf_pkg_path = Path(conf_project.__file__)
        # Print the versions of the repo
        version = conf_project.__version__

        # Write info message about repo version.
        summary = utils_config.check_imports_and_versions(globals().items())
        logger.info(summary)

        # Declare fov's as tuples
        # FIXME - get Lazuli FoV!!!
        # Using values from Pearl white paper
        logger.warning("FOV is hardcoded!")
        self.x_fov = 0.115 * 2  # [degrees]
        self.y_fov = 0.043 * 2  # [degrees]

        # vega V flux from https://www.gemini.edu/observing/resources/magnitudes-and-fluxes (3.68E-08 W/m2/um)
        # Multiply by 540nm (Johnson V-band central wavelength https://en.wikipedia.org/wiki/Photometric_system)
        self.vega_flux = {
            "V": 3.68e-08 * (540e-9 * 1e6)
        }  # Irradiance of Vega (in W/m^2)
        logger.debug(f"{self.vega_flux["V"]=:0.3e} [W/m2]")
        self.vega_mag = {"V": 0}  # setting incase of zero point offsets.

    def plot_pst(self, theta, pst, title, color, label, xlim=None, ylim=None):
        # determine range
        if xlim is None:
            xmax = np.nanmax(theta[pst > 1e-8])
            xmin = np.nanmin(theta[pst > 1e-8])
            xlim = (xmin, xmax)
        if ylim is None:
            ymax = 2
            ymin = 1e-8
            ylim = (ymin, ymax)

        plt.figure(figsize=(8, 5))
        plt.plot(theta, pst, marker="o", linestyle="-", color=color, label=label)
        plt.xlim(xlim)
        plt.ylim(ylim)
        plt.yscale("log")
        plt.xlabel(r"$\theta$ (degrees)")
        plt.ylabel("PST")
        plt.title(title)
        plt.legend()
        plt.grid(True, which="both", linestyle="--")
        plt.show(block=False)

    def calc_plate_scale(self):
        """Calculates the plate scale"""

    def calc_throughput(self):
        """Calculates throughput of the telescope."""

        logger.warning("Throughput is a placeholder and needs updating")
        throughput = 0.95**4

        return throughput

    def run_report(self, output_dir):
        # Method that is called by a generic script
        # needs to be in every budget class.

        # Read in PST data (theta and power in y and x dims)
        # Output needs to be normalized to center of the FoV, units in W/m2

        # Note that the filename is relative to the budget location
        pst_file = Path(self.scattered.budget_dir).joinpath(
            self.scattered.budget["inputs"]["pst_file"]["value"]
        )

        file_type = self.scattered.budget["inputs"]["pst_file"]["file_type"]
        theta_y, pst_y, theta_x, pst_x = self.read_pst(pst_file, file_type=file_type)

        pst_no_scatter_file = Path(self.scattered.budget_dir).joinpath(
            self.scattered.budget["inputs"]["pst_no_scatter_file"]["value"]
        )
        file_type = self.scattered.budget["inputs"]["pst_no_scatter_file"]["file_type"]

        theta_y_ns, pst_y_ns, theta_x_ns, pst_x_ns = self.read_pst(
            pst_no_scatter_file, file_type=file_type
        )

        # verify that the angles are the same
        # to within an arcsecond
        for i, theta in enumerate(theta_y):
            assert theta == pytest.approx(theta_y_ns[i], abs=1 / 3600.0)
        for i, theta in enumerate(theta_x):
            assert theta == pytest.approx(theta_x_ns[i], abs=1 / 3600.0)

        # Normalize PSTs
        if file_type == "fred_xlsx_v1":
            # psts are output as dataframes
            theta_y_full, pst_y_full_norm = self.pst_normalize_fred(
                theta_y, pst_y, pst_y_ns, axis="y"
            )
            theta_x_full, pst_x_full_norm = self.pst_normalize_fred(
                theta_x, pst_x, pst_x_ns, axis="x"
            )

        # # Plot raw PST Y data
        # plot_pst(theta_y_full, pst_y_full, r"PST for $\theta_y$ (Full Field)", 'b', "PST Y Full Range")

        # Plot normalized PST Y data
        # self.plot_pst(theta_y_full, pst_y_full_norm, r"Normalized PST for $\theta_y$ (Full Field)", 'r', "Normalized PST Y Full Range")

        # # Plot raw PST X data
        # plot_pst(theta_x_full, pst_x_full, r"PST for $\theta_x$ (Full Field)", 'b', "PST X Full Range")

        # # Plot normalized PST X data
        self.plot_pst(
            theta_x_full,
            pst_x_full_norm,
            r"Normalized PST for $\theta_x$ (Full Field)",
            "r",
            "Normalized PST X Full Range",
        )
        self.plot_pst(
            theta_y_full,
            pst_y_full_norm,
            r"Normalized PST for $\theta_y$ (Full Field)",
            "r",
            "Normalized PST Y Full Range",
        )
        plt.show()

        # Declare PSTs for the class

        self.theta_x = np.array(theta_x_full, dtype=float)
        self.pst_x = np.array(pst_x_full_norm, dtype=float)

        self.theta_y = np.array(theta_y_full, dtype=float)
        self.pst_y = np.array(pst_y_full_norm, dtype=float)

        #################################
        # Estimate sky coverage based on the brightness of a single star
        #  and it's relative location
        #################################

        # Relates a stellar magnitude and a PST value.
        # So what PST value corresponds to

        # Want to develop a surface magnitude vs zodi relationship.

        # Requirement (for Pearl, L3-0016) states, "Stray and scattered light,
        # as measured at the WCC focal plane (L3-0011) shall not exceed 1 zodi
        # over 90% of the sky outside of the galactic thick disc."

        zodi_arr = np.arange(-5, 5, 0.1)
        surf_fluxes, surface_mags = self.zodi_to_surf_flux(zodi_arr)

        # Want to be able to specify a list of magnitudes and
        # separations (in x and y) and return an expected surface flux.
        # Start by developing the relationship between

        # Only in the x-axis for now
        stellar_mags = [3.0, 9.0]
        separations_xy = [(0.3, 0.0), (0.4, 0.0)]
        total_flux, zodis, surface_mag = self.calc_surface_flux(
            stellar_mags, separations_xy
        )

        logger.info(f"{total_flux=:0.2e}")
        logger.info(f"{surface_mag=:0.3f}")
        logger.info(f"{zodis=:0.3f}")

        # estimate sky coverage by looking at the brightest stars
        logger.debug(f"Starting sky coverage calculation")

        # Convert to Watts/m^2/arcsec for a 0th magnitude star

        # Scale to magnitude Xth incident star

        # Calculate surface flux in zodi's and compare to requirement
        # Note requirement should be something like X% coverage above a surface magnitude of X zodi's.

        # calculate in a surface magnitude

        # Determine coverage for an Xth magnitude star with a radius of R

    def read_pst(self, filename, file_type=None):
        """Reads PST files. Currently only xlsx is supported which is the file
        that is exported by the FRED model.

        Output needs to be normalized to center of the FoV, units in W/m2

        Parameters:
        -----------

        file_type: str
            Input file type. Currently only 'fred_xlsx_v1' is supported.

        filename: str
            pathname of file containing pst information

        Returns:
        --------
        pst_y: array
            PST of y-axis [W/m2] but normalized by the value at the center of the field.
        pst_x: array
            PST of x-axis [W/m2] but normalized by the value at the center of the field.

        """

        # determine input file type
        if file_type == "fred_xlsx_v1":
            theta_y, pst_y = self.read_pst_fred(filename, axis="y")
            theta_x, pst_x = self.read_pst_fred(filename, axis="x")
        else:
            raise ValueError(f"Only xlsx file extensions supported.")

        return theta_y, pst_y, theta_x, pst_x

    def read_pst_fred(self, filename, axis=None):
        """Reads a PST file generated by FRED in excel (xlsx) format and extract into a pandas dataframe.
        Needs to be called for each axis.
        Output normalized to center of the FoV, units in W/m2

        Parameters:
        -----------

        axis: str
            Axis of PST, must be 'x' or 'y'

        filename: str
            pathname of file containing pst information

        Returns:
        --------
        pst_y: array
            PST of y-axis [W/m2] but normalized by the value at the center of the field.
        pst_x: array
            PST of x-axis [W/m2] but normalized by the value at the center of the field.

        """

        def _extract_data(df, start, end, col):
            """Extract data function.
            FIXME: I don't really understand what this does yet.
            """

            data = df.iloc[start:end, col].reset_index(
                drop=True
            )  # Reset index for alignment
            return data

        if "xlsx" in str(filename):
            if axis == "y":
                pst_df = pd.read_excel(
                    filename, sheet_name=0
                )  # First sheet (Y-axis PST)
            elif axis == "x":
                pst_df = pd.read_excel(filename, sheet_name="x_pst")  # X-axis PST
            else:
                raise ValueError(
                    f"Axis parameter must be set to 'x' or 'y' and not {axis}."
                )
        else:
            raise ValueError(f"Only xlsx file extensions supported.")

        if axis == "x":
            row_min = 2
            row_max = 237
        elif axis == "y":
            row_min = 2
            row_max = 225

        theta_full = _extract_data(pst_df, row_min, row_max, 0)
        pst_full = _extract_data(pst_df, row_min, row_max, 3)

        return theta_full, pst_full

    def pst_normalize_fred(self, angles, pst, pst_no_scatter, axis=None):
        """Normalizes Fred PSTs"""

        def _safe_normalize(pst, pst_ns):
            """Function for safe normalization that fully avoids division by zero.
            FIXME: Don't understand why this is doing this like this"""

            pst = pst.to_numpy()
            pst_ns = pst_ns.to_numpy()

            # Ensure both arrays have the same length
            min_length = min(len(pst), len(pst_ns))
            pst = pst[:min_length]
            pst_ns = pst_ns[:min_length]

            # Initialize with original values instead of zeros
            pst_norm = pst.copy()

            # Where ns values are nonzero, apply normalization
            nonzero_mask = pst_ns != 0
            pst_norm[nonzero_mask] = pst[nonzero_mask] / pst_ns[nonzero_mask]

            return pd.Series(pst_norm)  # Convert back to Pandas Series for plotting

        def _match_lengths(theta, pst):
            """Don't understand why this is required either"""
            min_length = min(len(theta), len(pst))
            return theta[:min_length], pst[:min_length]

        pst_full_norm = _safe_normalize(pst, pst_no_scatter)
        theta_norm, pst_norm = _match_lengths(angles, pst_full_norm)

        assert len(theta_norm) == len(pst_norm)

        # # Normalize safely (if ns = 0, use original)
        # pst_y_full_norm = self.safe_normalize(pst_y_full, pst_y_full_ns)
        # pst_x_full_norm = self.safe_normalize(pst_x_full, pst_x_full_ns)

        # theta_x_full, pst_x_full_norm = self.match_lengths(theta_x_full, pst_x_full_norm)
        # theta_y_full, pst_y_full_norm = self.match_lengths(theta_y_full, pst_y_full_norm)

        return theta_norm, pst_norm

    def zodi_to_surf_flux(self, zodis, wave=540e-9):
        """Return surface magnitudes for an array of zodical light levels.
        Note that 1 zodi is 22.1 mag/arcsec^2.

        Parameters:
        -----------

        zodis: array
            Array of number of zodi's to calculate surface flux and surface magnitudes

        wave: float
            Wavelength to calculate the value. Only 540nm is currently supported.
        """

        if wave != 540e-9:
            raise ValueError("Only a wavelength of 540e-9m is currently supported.")

        # From HST - high background (22.1 mag/sq arcsec) - defined as the earth-shine at 38° - https://hst-docs.stsci.edu/wfc3ihb/chapter-9-wfc3-exposure-time-calculation/9-7-sky-background#id-9.7SkyBackground-table9.4

        # Table 9.4 has 22.1 at ecliptic long = 45, lat = 30, also at 180,0
        # Then table 1 in the Levasseur paper puts that position at 195 S10.

        # From the hubble paper
        # 5.17E-18 ergcm−2 s−1 Å−1 arcsec−2
        # 10^7 ergs/ Joule
        zodi_flux1 = 5.17e-18 / 1e7 * (100**2) * 5500  # W/m2/arcsec2 at 0.55um
        logger.debug(f"{zodi_flux1=}")

        # From Levasseur
        zodi_flux2 = 195 * 1.261e-8 * 0.55 / 4.2545e10  # W/m2/arcsec2
        logger.debug(f"{zodi_flux2=}")

        # Use the hubble paper
        self.zodi_flux = zodi_flux1

        # What is the surface flux at each zodi?
        surface_fluxes = self.zodi_flux * zodis

        # flux/arcsec^2
        # Convert the total flux to an effective magnitude, using the standard flux of 22.1 mag/arcsec^2 per the zodi flux
        surface_mags = -2.5 * np.log10(surface_fluxes / self.zodi_flux) + 22.1

        return surface_fluxes, surface_mags

    def calc_surface_flux(self, stellar_mags, separations):
        """Determine total surface flux and magnitude for an array of stars

        Parameters:
        -----------

        stellar_mags: array
            Magnitudes for each star that is to be included in the determination of total background.

        separations: array
            Angular separation for each target in degrees

        Outputs:
        --------

        total_flux:
            Total flux in W/m2/arcsec

        total_flux_zodis:
            Flux in zodis

        total_flux_surface_mag:
            Flux in mag/arcsec^2
        """

        # loop over the stars
        star_flux = []
        star_pst = []
        total_flux = 0
        for i, mag in enumerate(stellar_mags):

            star_theta = separations[i]
            logger.debug(f"{i=},{mag=}, {star_theta=}\n")
            # project to x and y
            # Need to think about how to do this
            # FIXME: Just use X right now
            logger.warning("Using X-PST only for determining flux on focal plane.")
            star_theta_x = star_theta[0]  # * np.cos(star_phi[i])
            star_theta_y = star_theta[1]  # * np.sin(star_phi[i])

            star_flux_at_M1 = (
                10 ** (-(mag - self.vega_mag["V"]) / 2.5) * self.vega_flux["V"]
            )  # W/m2
            logger.debug(f"{star_flux_at_M1=:0.3e} [W/m2]\n")
            # interpolate PST to input angle

            star_pst_x = np.interp(star_theta_x, self.theta_x, self.pst_x)
            star_pst_y = np.interp(star_theta_y, self.theta_y, self.pst_y)

            # This doesn't work, should it be an average?
            # FIXME: Get assistance with PST definition

            # star_pst.append(np.sqrt(star_pst_x**2 + star_pst_y**2))
            # star_pst.append((star_pst_x + star_pst_y)/2.0)
            star_pst.append(star_pst_x)

            logger.debug(f"{star_pst_x=:0.3e},{star_pst_y=:0.3e},{star_pst[i]=:0.3e}\n")

            star_flux_per_WCC = star_flux_at_M1 * star_pst[i]  # W/m2/FoV

            fov_arcsec = (self.x_fov * self.y_fov) * 3600**2  # degrees to arcseconds
            star_flux_at_WCC = star_flux_per_WCC / (fov_arcsec)  # W/m2/arcsec
            logger.debug(f"{i=},{mag=:0.2f},{star_flux_at_WCC=:0.3e}\n")

            total_flux += star_flux_at_WCC

        # Now calculate in zodi's and surface flux
        # What is the surface flux at each zodi?
        zodis = total_flux / self.zodi_flux

        # flux/arcsec^2
        # Convert the total flux to an effective magnitude, using the standard flux of 22.1 mag/arcsec^2 per the zodi flux
        surface_mag = -2.5 * np.log10(total_flux / self.zodi_flux) + 22.1

        return total_flux, zodis, surface_mag

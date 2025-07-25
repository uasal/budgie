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
from astropy import units as u


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
        # should be ~4.5836 arcseconds/mm = ~0.00127 degrees/mm
        #
        self.plate_scale = (1e-3 * u.Unit('m') / u.Quantity(config['telescope']['general']['f_eff'])) * (180 * u.Unit('deg')/np.pi) / u.Unit('mm')
        # Get pupil area
        # note the 0.5's because the diameters are in the configs and not radii
        self.pupil_area = np.pi * ((0.5*u.Quantity(config['telescope']['optics']['m1']['aper_clear_OD']))**2) - np.pi*((0.5*u.Quantity(config['telescope']['optics']['m1']['aper_clear_ID']))**2)

        self.x_center = u.Quantity(self.scattered.budget['inputs']['pst_file']['x_center'])
        # self.y_center = (-0.15+0.075)/2 * u.Unit('deg')
        self.y_center = u.Quantity(self.scattered.budget['inputs']['pst_file']['y_center'])
        self.x_fov = u.Quantity(self.scattered.budget['inputs']['pst_file']['x_fov']) * self.plate_scale  # [degrees]
        self.y_fov = u.Quantity(self.scattered.budget['inputs']['pst_file']['y_fov']) * self.plate_scale  # [degrees]

        # Read in PST data (theta and power in y and x dims)
        # Output is in W at the focal plane

        # Note that the filename is relative to the budget location
        pst_file = Path(self.scattered.budget_dir).joinpath(
            self.scattered.budget["inputs"]["pst_file"]["value"]
        )

        file_type = self.scattered.budget["inputs"]["pst_file"]["file_type"]
        _theta_y, _pst_y, _theta_x, _pst_x = self.read_pst(pst_file, file_type=file_type)

        # Declare PSTs for the class
        self.theta_x = np.array(_theta_x, dtype=float)
        self.pst_x = np.array(_pst_x, dtype=float)

        self.theta_y = np.array(_theta_y, dtype=float)
        self.pst_y = np.array(_pst_y, dtype=float)

        # The following should probably come from the astrophysics.toml file.
        # vega V flux from https://www.gemini.edu/observing/resources/magnitudes-and-fluxes (3.68E-08 W/m2/um)
        # Multiply by 540nm (Johnson V-band central wavelength https://en.wikipedia.org/wiki/Photometric_system)
        _vega_flux = 3.68e-08 * u.Unit('W/(m2 um)')
        self.wave_cen = 540e-9 * u.Unit('m') # central wavelength
        self.vega_flux = {
            "V": (_vega_flux * self.wave_cen).to('W / m2')
        }  # Irradiance of Vega (in W/m^2)
        logger.debug(f"{self.vega_flux["V"]=:0.3e}")
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


    def run_report(self, output_dir):
        # Method that is called by a generic script
        # needs to be in every budget class.


        # # Plot normalized PST X data
        self.plot_pst(
            self.theta_x,
            self.pst_x,
            r"Normalized PST for $\theta_x$ (Full Field)",
            "r",
            "Normalized PST X Full Range",
        )
        self.plot_pst(
            self.theta_y,
            self.pst_y,
            r"Normalized PST for $\theta_y$ (Full Field)",
            "r",
            "Normalized PST Y Full Range",
        )
        plt.show()


        ###################################################
        # Estimate sky coverage based on the brightness of 
        # a single star and it's relative location
        ###################################################

        # Relates a stellar magnitude and a PST value.
        # So what PST value corresponds to

        # Want to develop a surface magnitude vs zodi relationship.

        # Requirement (for Pearl, L3-0016) states, "Stray and scattered light,
        # as measured at the WCC focal plane (L3-0011) shall not exceed 1 zodi
        # over 90% of the sky outside of the galactic thick disc."

        zodi_arr = np.arange(1e-2, 5, 0.01) # number of zodis
        surf_fluxes, surface_mags = self.zodi_to_surf_flux(zodi_arr)

        # Want to be able to specify a list of magnitudes and
        # separations (in x and y) and return an expected surface flux.
        # Start by developing the relationship between

        # Only in the x-axis for now
        stellar_mags = [4.0]#, 9.0]
        separations_xy = [(0.51, 0.0),]# (0.4, 0.0)]

        total_flux, zodis, surface_mag = self.calc_surface_flux(
            stellar_mags, separations_xy
        )

        logger.info(f"{total_flux=:0.2e}")
        logger.info(f"{surface_mag=:0.3f}")
        logger.info(f"{zodis=:0.3f}")

        # estimate sky coverage by looking at the brightest stars
        logger.debug(f"Starting sky coverage calculation")

        # Determine coverage for an Xth magnitude star with a radius of R

    def read_pst(self, filename, file_type=None):
        """Reads PST files. Currently only xlsx is supported which is the file
        that is exported by the FRED model.

        Values is normalized by the power incident on the entrance aperture so that
        on-axis (and in field), the PST value will effectively be the throughput.

        Output is therefore unitless.

        Parameters:
        -----------

        file_type: str
            Input file type. Currently only 'fred_xlsx_v1' is supported.

        filename: str
            pathname of file containing pst information

        Returns:
        --------
        pst_y: array
            PST of y-axis [W/m2].
        pst_x: array
            PST of x-axis [W/m2].

        """

        # determine input file type
        if "fred_xlsx_v1" in file_type:
            raise OSError("fred_xlsx_v1 is no longer supported.")
        
        elif "fred_xlsx_v2" in file_type:
            theta_y, pst_y = self.read_pst_fred(filename, axis="y", file_type=file_type)
            theta_x, pst_x = self.read_pst_fred(filename, axis="x", file_type=file_type)
        else:
            raise ValueError(f"Only xlsx file extensions supported.")

        return theta_y, pst_y, theta_x, pst_x

    def read_pst_fred(self, filename, axis=None, file_type=None):
        """Reads a PST file generated by FRED in excel (xlsx) format and extract into a numpy array.
        Needs to be called for each axis.

        Note that the power in the spreadsheet is in W as measured at the focal plane.
        This is normalized by the power incident on the entrance aperture so that
        on-axis (and in field), the PST value will effectively be the throughput.

        We do not use the ratio value in the spreadsheet as it does not have the area correction in it.ß

        Output is therefore unitless.

        Parameters:
        -----------

        axis: str
            Axis of PST, must be 'x' or 'y'

        filename: str
            pathname of file containing pst information

        Returns:
        --------
        pst_y: array
            PST of y-axis [W] but normalized by the value at the center of the field.
        pst_x: array
            PST of x-axis [W] but normalized by the value at the center of the field.

        """

        if file_type == None:
            raise OSError("A filetype must be provided. Supported filetypes are fred_xlsx_v2")

        if "xlsx" in str(filename):
            if axis == "y":
                pst_df = pd.read_excel(
                    filename, sheet_name="y_pst",header=1
                )  # First sheet (Y-axis PST)
            elif axis == "x":
                pst_df = pd.read_excel(filename, sheet_name="x_pst", header=1)  # X-axis PST
            else:
                raise ValueError(
                    f"Axis parameter must be set to 'x' or 'y' and not {axis}."
                )
        else:
            raise ValueError(f"Only xlsx file extensions supported.")

        # Revert to numpy arrays:
        if file_type == 'fred_xlsx_v2':
            theta = pst_df['Angle'].to_numpy(dtype=float) *u.Unit('deg')
            pst = pst_df['Power at Detector aka PST (P_d)'].to_numpy(dtype=float) *u.Unit('W')
            incident_power = pst_df['Power at First Vane (P_1)'].to_numpy(dtype=float)*u.Unit('W')
            incident_area = pst_df['Projected Area Size of First Vane (A_1)'].to_numpy(dtype=float) *u.Unit('mm2')
        else:
            raise OSError('Only file_type of fred_xlsx_v2 is supported.')

        
        # Area of entrance for simulation is slightly different than
        # the area of the entrance pupil, so need to scale slightly.
        if axis == "y":
            area = np.interp(self.y_center, theta, incident_area)
            power = np.interp(self.y_center, theta, incident_power)
        elif axis == "x":
            area = np.interp(self.x_center, theta, incident_area)
            power = np.interp(self.x_center, theta, incident_power)
        else:
            raise OSError('No axis specified.')
        
        scaling_factor = self.pupil_area.to('mm2') / area
        logger.debug(f'Area scaling factor is {scaling_factor}')
        pst = pst * scaling_factor

        # Now normalize by the light incident on the entrance pupil
        pst/=power

        return theta, pst

    
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
        # at 5500, this corresponds to 5.17E-18

        # Table 9.4 has 22.1 at ecliptic long = 45, lat = 30, also at 180,0
        # Then table 1 in the Levasseur paper puts that position at 195 S10.

        # From the hubble paper site
        # 5.17E-18 ergcm−2 s−1 Å−1 arcsec−2
        # 10^7 ergs/ Joule
        zodi_flux1 = (5.17e-18 / 1e7 * (100**2) * 5500)*u.Unit('W / (m2 arcsec2)')  # W/m2/arcsec2 at 0.55um, which is 2.84e-17 W/ (arcsec2 m2)
        logger.debug(f"{zodi_flux1=}")

        # From Levasseur
        zodi_flux2 = 195 * 1.261e-8 * 0.55 / 4.2545e10  # W/m2/arcsec2   -- 3.18e-17 W/ (arcsec2 m2)
        logger.debug(f"{zodi_flux2=}")

        # Use the Hubble paper
        self.zodi_flux = zodi_flux1

        # What is the surface flux at each zodi?
        surface_fluxes = self.zodi_flux * zodis

        # flux/arcsec^2
        # Convert the total flux to an effective magnitude, using the standard flux of 22.1 mag/arcsec^2 per the zodi flux
        surface_mags = -2.5 * np.log10(surface_fluxes / self.zodi_flux) + 22.1

        return surface_fluxes, surface_mags

    def calc_surface_flux(self, stellar_mags, separations):
        """Determine total surface flux and magnitude for an array of stars.


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
            # Need to think about how to do this in 2d
            # FIXME: Just use X right now
            logger.warning("Using X-PST only for determining flux on focal plane.")
            star_theta_x = star_theta[0]  # * np.cos(star_phi[i])
            star_theta_y = star_theta[1]  # * np.sin(star_phi[i])

            star_flux_density_at_M1 = (
                10 ** (-(mag - self.vega_mag["V"]) / 2.5) * self.vega_flux["V"]
            )  # W/m2
            logger.debug(f"{star_flux_density_at_M1=:0.3e} [W/m2]\n")

            # interpolate PST to input angle
            star_pst_x = np.interp(star_theta_x, self.theta_x, self.pst_x)
            star_pst_y = np.interp(star_theta_y, self.theta_y, self.pst_y)

            # How to combine y and x? Should it be an average?
            # FIXME: Get assistance with PST definition
            # star_pst.append(np.sqrt(star_pst_x**2 + star_pst_y**2))
            # star_pst.append((star_pst_x + star_pst_y)/2.0)

            star_pst.append(star_pst_x)

            logger.debug(f"{star_pst_x=:0.3e},{star_pst_y=:0.3e},{star_pst[i]=:0.3e}\n")

            # PST is the ratio of intensity at the entrance pupil (watts) to
            # intensity at the focal plane (watts)
            star_flux_per_WCC = star_flux_density_at_M1 *self.pupil_area* star_pst[i]  # W/FoV

            fov_arcsec = (self.x_fov * self.y_fov).to('arcsec2') # degrees to arcseconds
            star_flux_at_WCC = star_flux_per_WCC / (fov_arcsec)  # W/arcsec
            logger.debug(f"{i=},{mag=:0.2f},{star_flux_at_WCC=:0.3e}\n")

            total_flux += star_flux_at_WCC

        # Now calculate in zodi's and surface flux
        # What is the surface flux at each zodi?

        zodi_flux_at_WCC = (self.zodi_flux*self.pupil_area)

        zodis = total_flux / zodi_flux_at_WCC

        logger.info(f'Total flux is {total_flux:0.2e}, which corresponds to {zodis:0.2f} zodis.')

        # flux/arcsec^2
        # Convert the total flux to an effective magnitude, using the standard flux of 22.1 mag/arcsec^2 per the zodi flux
        surface_mag = -2.5 * np.log10(total_flux / zodi_flux_at_WCC) + 22.1

        return total_flux, zodis, surface_mag

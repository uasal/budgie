from pathlib import Path
from budgie import set_directory
import pytest
import numpy as np
from astropy import units as u

# Set the directory of the test data
set_directory(Path(__file__).parents[1].joinpath("tests/data"))

from budgie import ScatteredLight

def test_zodi_to_surf_flux():
    """Much of this is a units conversion test and verification of code during development.
    Also tests calc_surface_flux """

    test_budget = "test_scattered_light_budget.yaml"
    scattered = ScatteredLight(test_budget)
    zodi_arr = np.array((1,2.5)) # number of zodis

    surf_fluxes, surface_mags = scattered.zodi_to_surf_flux(zodi_arr)

    # zodi flux from Hubble paper is : 5.17E-18 ergcm−2 s−1 Å−1 arcsec−2
    wave = 5500 * u.Unit('Angstrom')
    zodi_flux = u.Quantity(5.17E-18 * u.Unit('erg / (cm2 s Angstrom arcsec2)'))

    # check manual calc with astropy
    zodi_flux_units = (zodi_flux*wave).to('W / (m2 arcsec2)')

    exp = u.Quantity(2.84e-17 * u.Unit('W/ (arcsec2 m2)'))  
    assert np.abs(zodi_flux_units-exp)/exp < 0.01

    # zodi flux is 2.84e-17 W/ (arcsec2 m2)
    exp = u.Quantity(2.84e-17 * u.Unit('W / (m2 arcsec2)'))

    assert np.abs(surf_fluxes[0]-exp)/exp < 0.01

    assert np.abs(surf_fluxes[1]-exp*zodi_arr[1])/(exp*zodi_arr[1]) < 0.01

    assert surface_mags[0] == 22.1

    # 2.5 increase in flux should be an decrease of 1 magnitude
    assert np.abs(surface_mags[1]-21.1) <=0.01 


    # declare stellar magnitudes and separations to test calculations of fluxes
    # Start with a zeroth mag on axis, PST value should just be throughput.
    stellar_mags = [0]
    separations = [(0,0)]

    total_flux, zodis, surface_mag = scattered.calc_surface_flux(stellar_mags, separations)

    # On axis, we should get 100% of the starlight, multiplied by the transmission
    # from https://www.gemini.edu/observing/resources/magnitudes-and-fluxes
    vega_flux = u.Quantity(2.50E-08  * u.Unit('W / (m2 um)'))
    vega_flux = 3.68e-08 * u.Unit('W/(m2 um)') # Johnson V, same as inside budget
    pupil_area = u.Quantity(np.pi*(3.0/2)**2  * u.Unit('m2'))
    wavelength = u.Quantity(0.550  * u.Unit('um'))
    transmission = 0.99**4 # I think this is what Max told me
    fov_arcsec = (scattered.x_fov * scattered.y_fov).to('arcsec2')
    exp=vega_flux*pupil_area*wavelength*transmission/fov_arcsec

    assert np.abs(total_flux-exp)/exp <=0.05 

    # Now go slightly off axis (in x only)

    stellar_mags = [0]
    separations = [(0.5,0)]
    # value gets interpolated in the code, but we can manually approximate it here
    # Note the spacing is 0.13 degrees, so it'd be just an average of the two
    # pst values.
    pst_expectation = (2.07E-05 + 1.86E-05)/2

    exp2 = exp*pst_expectation

    total_flux, zodis, surface_mag = scattered.calc_surface_flux(stellar_mags, separations)

    assert np.abs(total_flux-exp2)/exp2 <=0.05

test_zodi_to_surf_flux()
#from importlib.metadata import PackageNotFoundError, version
#import sys
from budgie.version import __version__

from budgie.core import (
    MissionLifetime,
    TransientResponse,
    WaveFrontError,
    Budget,
    Plantuml_Writer,
    ScatteredLight,
    find_vals,
    set_directory,
)

__project__ = "budgie"

CLI = "budgie"
VERSION = "{0} v{1}".format(__project__, __version__)
DESCRIPTION = "budgie and margin calculation."

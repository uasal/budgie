#from importlib.metadata import PackageNotFoundError, version
#import sys
from budgie.version import __version__

from budgie.core import (
    MissionLifetime,
    TransientResponse,
    WaveFrontError,
    Budget,
    Plantuml_Writer,
    find_vals,
    set_directory,
)

from budgie.core.tests import (
    TestBudgets,
    TestWaveFrontError,
)
__project__ = "budgie"


CLI = "budgie"
VERSION = "{0} v{1}".format(__project__, __version__)
DESCRIPTION = "budgie and margin calculation."

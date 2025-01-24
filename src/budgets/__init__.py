#from importlib.metadata import PackageNotFoundError, version
#import sys
from budgets.version import __version__

from budgets.core import (
    MissionLifetime,
    TransientResponse,
    WaveFrontError,
    Budget,
    find_vals,
    set_directory,
)

from budgets.core.tests import (
    TestBudgets,
    TestWaveFrontError,
)
__project__ = "budgets"


CLI = "budgets"
VERSION = "{0} v{1}".format(__project__, __version__)
DESCRIPTION = "Budgets and margin calculation."

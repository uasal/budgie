#from importlib.metadata import PackageNotFoundError, version
#import sys
try:
    from budgie.version import __version__
except ModuleNotFoundError:  # pragma: no cover - fallback for editable/source usage
    __version__ = "0+unknown"

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
from budgie.tree import (
    BudgetNode,
    BudgetTreeError,
    build_tree,
    compile_to_pdf,
    display_tree,
    render_ascii,
    render_tikz,
)
__project__ = "budgie"


CLI = "budgie"
VERSION = "{0} v{1}".format(__project__, __version__)
DESCRIPTION = "budgie and margin calculation."

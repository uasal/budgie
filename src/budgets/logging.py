import argparse
import logging
import yaml


def _trace(self, message, *args, **kws):
    if self.isEnabledFor(logging.DEBUG - 1):
        self._log(logging.DEBUG - 1, message, args, **kws)  # pylint: disable=W0212


logging.addLevelName(logging.DEBUG - 1, "TRACE")
logging.Logger.trace = _trace  # type: ignore

logger = logging.getLogger
log = logger(__name__)

# exception classes ##########################################################


class BudgetError(Exception):
    """Generic error."""

class BudgetFileError(BudgetError, IOError):
    """Raised on IO errors."""


class BudgetWarning(BudgetError, Warning):
    """Generic Doorstop warning."""


class BudgetInfo(BudgetWarning, Warning):
    """Generic Doorstop info."""

# logging classes ############################################################


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """Command-line help text formatter with wider help text."""

    def __init__(self, *args, **kwargs):
        kwargs["max_help_position"] = 40
        super().__init__(*args, **kwargs)


class WarningFormatter(logging.Formatter):
    """Logging formatter that displays verbose formatting for WARNING+."""

    def __init__(self, default_format, verbose_format, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_format = default_format
        self.verbose_format = verbose_format

    def format(self, record):
        """Python 3 hack to change the formatting style dynamically."""
        if record.levelno > logging.INFO:
            self._style._fmt = self.verbose_format  # pylint: disable=W0212
        else:
            self._style._fmt = self.default_format  # pylint: disable=W0212
        return super().format(record)


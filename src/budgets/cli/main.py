import argparse
import sys
import os
from budgets import logging


# STILL IN DEVELOPMENT
# Using doorstop-ewan / doorstop as an example for this.

log = logging.logger(__name__)

def main(args=None):
    """Processes command arguments to use budgets"""
    from budgets import CLI, VERSION, DESCRIPTION


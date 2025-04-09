import argparse
import sys
import os
from budgie import logging


# STILL IN DEVELOPMENT
# Using doorstop-ewan / doorstop as an example for this.

log = logging.logger(__name__)

def main(args=None):
    """Processes command arguments to use budgie"""
    from budgie import CLI, VERSION, DESCRIPTION


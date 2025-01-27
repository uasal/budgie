import yaml
import os

# Placeholder for potentially moving findvals too and future basic methods that can be called from that do not necessary pertain to the Budget class.

# disk helper functions ######################################################

def create_dirname(path):
    """Ensure a parent directory exists for a path."""
    dirpath = os.path.dirname(path)
    if dirpath and not os.path.isdir(dirpath):
        #log.info("creating directory {}...".format(dirpath))
        os.makedirs(dirpath)





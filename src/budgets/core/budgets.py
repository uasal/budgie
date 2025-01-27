from abc import ABCMeta, abstractmethod
import typing
from pathlib import Path
import numpy as np
import yaml


def set_directory(budget_dir):
    """"Sets Budget Data Path for all budgets"""
    global BUDGET_DATA_DIR
    BUDGET_DATA_DIR = Path(__file__).parents[2].joinpath(budget_dir)

    return BUDGET_DATA_DIR


def find_vals(d, key):
    """Generator that is used to find all instances of a given keyword in a dictionary or list."""
    # Code from https://stackoverflow.com/questions/71850069/get-all-values-by-a-specific-key-in-a-deep-nested-dict-using-python
    if isinstance(d, dict):
        for k, v in d.items():
            if k == key:
                print(f"{key=}, {v=}")
                yield v
            else:
                yield from find_vals(v, key)
    elif isinstance(d, list):
        # this is for if the input is a list, which isn't used here.
        for v in d:
            yield from find_vals(v, key)


class Budget(metaclass=ABCMeta):
    """
    Abstract base class for Budgets.
    All functions marked as @abstractmethod must be defined in their subclass.
    Any functions that are standard for all budgets to use can be overridden if needed
    Point of this is to derive an initial image quality budget example.
    Units shall be consistent with AstroPy units.
    This schema does not allow additional fields: additionalProperties is False
    """

    def __init__(self, name):
        """Initializing the budget class."""
        self.name = name
        self.budget_dir = BUDGET_DATA_DIR
        self.budget = None
        self.get_budget()

    def get_name(self):
        return self.name

    def get_budget(self) -> dict[str, typing.Any]:
        """
        Reads in budget
        """

        print(self.name)
        schema_yaml = self.budget_dir.joinpath(self.name)

        print(f"{schema_yaml=}")
        self.budget = yaml.safe_load(Path(schema_yaml).read_text())

    def calc_margins(self, rss=True, sum=False):
        """Goes through and finds allocations and calculates margins"""

        # Allocations can only go 2 layers deep or this code will break
        # this is surely better done using recursion
        # Cannot change the arrays (meaning add keys) while looping, so need to capture the keys as a list and then loop over again later.

        places = []

        for key1, value1 in self.budget.items():
            if isinstance(value1, dict):
                for key2, value2 in value1.items():
                    # Occurs if allocation is in the 2nd layer, so in this case one must loop over all keys at the same layer, see if there is a second layer, then grab the cbes/specs.
                    if key2 == "allocation":
                        # print(f'allocation! - {key1=},{value1=},{key2=},{value2=}')
                        places.append(
                            [key1, value1, value2]
                        )  # stores high level key, set of values with it, and the allocation value
                    if isinstance(value2, dict):
                        for key3, value3 in value2.items():
                            if key3 == "allocation":
                                # print(
                                #     f"allocation2! - {key1=},{key2=},{value2=},{value3=}"
                                # )
                                places.append(
                                    [key1, key2, value2, value3]
                                )  # stores high level key, set of values with it, and the allocation value

            else:
                if key1 == "allocation":
                    # print(f"allocation2! - {key1=},{value1=}")
                    raise IOError("I don't know if this can happen?")

        for p in places:
            if len(p) == 3:
                key1 = p[0]
                value1 = p[1]  # dict of values
                value2 = p[2]  # allocation
                # print("In calc margins area.")
                print(value1)
                if rss:
                    # print("in RSS section!")
                    calc_spec, calc_cbe = self.rss_values(value1)
                else:
                    # print("in sum section!")
                    calc_spec, calc_cbe = self.sum_values(value1)
                self.budget[key1]["curr_spec"] = calc_spec
                self.budget[key1]["curr_cbe"] = calc_cbe
                self.budget[key1]["margin_spec"] = value2 - calc_spec
                self.budget[key1]["margin_cbe"] = value2 - calc_cbe
            elif len(p) == 4:
                key1 = p[0]
                key2 = p[1]
                value2 = p[2]  # dict of values
                value3 = p[3]  # allocation
                if rss:
                    #print("HERE")
                    print(f"{value2=}")
                    calc_spec, calc_cbe = self.rss_values(value2)
                else:
                    calc_spec, calc_cbe = self.sum_values(value2)
                self.budget[key1][key2]["curr_spec"] = calc_spec
                self.budget[key1][key2]["curr_cbe"] = calc_cbe
                self.budget[key1][key2]["margin_spec"] = value3 - calc_spec
                self.budget[key1][key2]["margin_cbe"] = value3 - calc_cbe

    def rss_values(self, values):
        """Finds values associated with an allocation.
        Calculates root sum squared of spec and cbe"""
        ss_spec = 0
        ss_cbe = 0
        for _, v in values.items():
            # print(f'{k=},{v=}')
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    if k2 == "cbe":
                        # print(v2)
                        # print(f'{k2=},{v2=}')
                        ss_cbe += v2 ** 2
                    elif k2 == "spec":
                        # print(v2)
                        # print(f'{k2=},{v2=}')
                        ss_spec += v2 ** 2
        return (np.sqrt(ss_spec), np.sqrt(ss_cbe))

    def sum_values(self, values):
        """Finds values associated with an allocation.
        Calculates root sum squared of spec and cbe"""
        ss_spec = 0
        ss_cbe = 0
        for _, v in values.items():
            # print(f'{k=},{v=}')
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    if k2 == "cbe":
                        # print(f'{k2=},{v2=}')
                        ss_cbe += v2
                    elif k2 == "spec":
                        # print(f'{k2=},{v2=}')
                        ss_spec += v2

        return (
            np.sum(ss_spec),
            np.sum(ss_cbe),
        )

    def run_report(self, output_dir):
        """ Runs report for budget and outputs to the specified directory.
        :param output_dir: string to output directory path
        """
        # This will change depending on budget / subclasses
        raise NotImplementedError

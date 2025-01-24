# STP Budget Package Description

The budget package is to be designed as a python package with a class that can perform multiple functions for the user:
- Read in the machine readable table for the budget
- read in the observatory and instrument toml files
- Provide a structure where a user can input code where key numbers are calculated based on the inputs above.
- A function which executes said code on instantiation (if desired), or later on.

A testing capability should also be included, arguably as a different method, which then runs checks against previous values which are potentially stored in the `stp_reference_data` toml files.
- Hardcoding a value in the test is probably ok, so long as there is a reference to the test. 
	- Getting the number out of the requirements is probably a step too far.

Because of the interdependency of budgets, I think it would be useful for them to live in a single repo. They could be uniquely named in a folder in the src directory (e.g. `src/budgets/iq.py`)

It's possible that each budget will need a "data" directory where it can put files that has values used for calculations, such as a sensitivity matrix. I suggest a `data/<budget_name>` directory at the top level. Also supporting documentation in `docs/<budget_name>`.

A user could instantiate a high-level class as:
```python
import stp_budgets

# Instantiating the class would read in either the CBE or spec values
iq = stp_budgets.IQ(cbe=True)

# Users can access the spec or CBE
print(f"Spec is {iq.static.M1.rms.spec}, CBE is {iq.static.M1.rms.cbe}")

# However, the class also outputs a generic parameter called "value", which is populated by whatever the class is instantiated with. This is useful for writing code using either number.

assert iq.static.M1.rms.value == iq.static.M1.rms.cbe

```

The `iq.py` class would have a standard set of functions, based upon the following template.

```python
import stp_reference_data
import yaml
import stp_budgets.utils

class Budget: #  
  def __init__(self, spec=True, cbe=False):  

	# reads in required toml files from stp_reference_data, or maybe importing the class just brings in all the data by default?
	self.obs_data = stp_reference_data.observatory

	# Read in budget table
	budget=yaml.load(IQ.yaml)

	# run whatever method creates the value keyword
	stp_budgets.utils(self.obs_data,spec=spec,cbe=cbe)

  def execute()
  # Required method, Executes whatever calculations need to be done.
  # all outputs should be grouped into a namespace
  self.iq.output.sensitivity = self.calculate_sensitivity(iq.obs_data.M1_diam, iq.coating.M1)

self.iq.output.exp_time = self.exp_time(iq.obs_data.M1_diam, iq.coating.M1, 0)

  def calculate_sensitivity(self, diam, coating)
  # User-created method to calculate and return sensitivity value
	magnitude = 0 # always assume a mag=0 star
    sens = diam*coating*magnitude
    return sens

  def calculate_exp_time(self, diam, coating)
  # User-created method to calculate and return an exposure time value
	time = diam/coating
    return time

  def checks()
  # Required method, although empty by default
  # also this needs a new name.

	max_time = 1000 # from L2-XYZZ
	assert self.iq.output.exp_time < max_time

```

With the standard class in place, of course there should be a standard set of pytests that make sure it has the correct structure etc.
Users can/should also have tests for their individual functions.

Continuing from the first code block above, where the class was instantiated, users can execute the calculations inside the class, execute checks (if desired) to see if some value exceeded some threshold, and then ultimately do some sort of pretty-print of the budget.

```python

iq.execute() # Calculates whatever values should be done

iq.checks() # Runs checks

# print it out in a nice way
stp_budgets.utils(iq)

```

## What does a budget file look like?

Specs and CBEs, along with a note on their traceability will live in the document. 
YAML files are useful for tables which have multiple tiers. In the cases where the budgets are much simpler, TOML files can be used as well. Presumably this will be the majority.

Still trying to capture this (see the TOML/YAML formatting heading below). Specifically with regards to where the margin lives and how we handle multi-level tables, but this is an example

A more complex example can be found in [tests/data/test_budget.yaml](../tests/data/test_budget.yaml)

A simplified example, which (unsurprisingly) is analogous to what is done with `observatory.toml` is found [tests/data/test_budget.toml](../tests/data/test_budget.toml)

## Outstanding issues/questions

### TOML/YAML formatting

For any utilities to work, the class needs to produce an object which is consistent in format, regardless of the file format used for holding the budget (e.g. TOML or YAML).
There are a few driving use cases here:

1. We should make the `stp_reference_data` TOML look/feel the same.
2. To remove duplication, it is useful to have specs, cbe's, and goals in the same file.
3. The files should be easily readable, so complicated nested tables should be an exception and not a standard.

So how do we handle the fact that some parameters do not have or need cbe's and goals, and how do we handle when they do need them but they don't have them?

Proposal:
- Any parameter that does not have a `_cbe` or `_goal` suffix will use the base value regardless of if the class is instantiated with `cbe=True`
- Descriptions can live in TOML comments, but these will never leave the file cannot be parsed, and therefore can never be rendered as part of any documentation.
- Those of us wanting a more standardized object will either use YAML with a more standardized format, or will write a function to map the configuration file to the appropriate format.

In the event that we want duplicate files, such as what might need to be done to simultaneously support the current `observatory.toml` file and a new version, we'll write a unit test to ensure numbers are the same and produce a warning for deprecation of the older format for X months until people adapt their code accordingly.
Of course, should people need help adapting we'll provide assistance. 

Although moderately unpalatable, one might consider breaking `observatory.toml` into multiple files (e.g. `WCC.toml`, `telescope.toml` etc).

### Calculating Margin

One interesting use-case is examining the CBEs vs specs and measuring margin. It's unclear to me at the moment how to do this from within this class as it requires instantiating itself in two ways.

One better solution might be to use an outside utility.


```python
import stp_budgets

# Instantiating the class would read in either the CBE or spec values
iq_cbe = stp_budgets.IQ(cbe=True)
iq_spec = stp_budgets.IQ() # loads spec by default.

margins = stp_budgets.utils.calc_margins(iq_cbe,iq_spec)

```

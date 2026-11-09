# Budgie
_Budgie the budget tool_

**NOTE:** In order for this to work, data yaml files must be added to the data directory (currently) but will be able to specify in the future via command line. Name of package is budgets currently but will be changed over to budgie per opened issues.

Use the `test.sh` and edit the data file names with the names of the actual ones added to the data directory to run a report test for the budgets added. This will install the budgie package as well in the process.

## Plantuml Diagrams
A 'demo' for visualizing the initial budget yaml files is added to this tool and requires [`plantuml`](https://plantuml.com) (plantuml.jar is provided).

**Future Implementation:** Using just graphviz or something similar will require some modifications on the `budgets.py` to prevent repeating of some code aspects and improve reporting mechanics. Plantuml will no longer be needed for the diagram portion in that implementation. In order to use `budgie`, you do **not** need to have plantuml for the other functions.

## Combining Terms (`combine`)
Each group that has an `allocation` adds up its terms' `spec` and `cbe` values to get its current spec/CBE and its margin. By default the rule comes from the budget: the wavefront error and mission lifetime budgets RSS their terms, while the transient response and DM stroke budgets sum them.

To override the rule for a single group, add a `combine` key set to `"rss"` or `"sum"`:

```yaml
static_optics:
  units: "nm"
  combine: "rss"   # terms are independent, so RSS them
  allocation: 300
  telescope:
    spec: 89.3
    cbe: 89.3
  esc:
    spec: 75
    cbe: 75
```

- Any other value raises a `ValueError`.
- A group has a single rule. If some terms need RSS and others need summing, put them in separate groups.
- Allocations can be at most two levels deep.
- Writing `combine` on every group, even when it matches the default, makes the YAML easier to read.

## DM Stroke Budget
`DMStroke` tracks how much of a deformable mirror's stroke is used, and how much is left, against the stroke the DM can deliver.

- **Units:** peak-to-valley **surface** stroke in nm. At (near) normal incidence, surface = wavefront / 2.
- **Available stroke:** `dm.surface_deflection` is the maximum stroke in the budget, and every allocation draws from it.
- **Groups:** terms within a group are summed by default, because stroke demands can stack on the same actuator. Set `combine: "rss"` on groups whose terms are independent. Group totals are always summed into the total stroke used.
- **RMS inputs:** a peak-to-valley budget needs PV values. If a source gives RMS wavefront error, convert it with an assumed PV/RMS factor and record the inputs in the term, as shown below. `rms_wfe` and `rms_to_pv` are for reference only, and the calculation uses `spec`/`cbe`, so update those yourself whenever the inputs change.

```yaml
dm:
  units: "nm"
  surface_deflection: 1400  # maximum stroke available in the budget

dynamic:
  units: "nm"
  combine: "sum"
  allocation: 100
  los_compensation:
    rms_wfe: 28    # nm RMS wavefront
    rms_to_pv: 5   # assumed PV/RMS scaling factor
    spec: 70       # rms_wfe * rms_to_pv / 2
    trace: "Source document and calculation"
    cbe: 70
    cbe_trace: "Source of the current best estimate"
```

To run the report, put `dm_stroke.yaml` in the `data` directory and run:

```bash
python scripts/run_report.py dm_stroke.yaml
```

This writes `reports/dm-stroke-report.md`. The report lists the available stroke, the allocated stroke, the unallocated reserve, the spec and CBE totals, and the margins. It also warns if the allocations exceed the available stroke. See [tests/data/test_dm_stroke.yaml](tests/data/test_dm_stroke.yaml) for a complete example.

## Related Documents
- [STP Budget Package Description](docs/design_description.md)


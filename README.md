# Budgie
_Budgie the budget tool_

Originally on GitLab: https://gitlab.sc.ascendingnode.tech:8443/pearl-systems/budgets but tool portion was moved out of GitLab to GitHub for accessibility. Source budget yaml files are on GitLab still with any other related documentation that is specific to them.

**NOTE:** In order for this to work, data yaml files must be added to the data directory (currently) but will be able to specify in the future via command line. Name of package is budgets currently but will be changed over to budgie per opened issues.

Use the `test.sh` and edit the data file names with the names of the actual ones added to the data directory to run a report test for the budgets added. This will install the budgie package as well in the process.

## Plantuml Diagrams
A 'demo' for visualizing the initial budget yaml files is added to this tool and requires [`plantuml`](https://plantuml.com) (plantuml.jar is provided).

**Future Implementation:** Using just graphviz or something similar will require some modifications on the `budgets.py` to prevent repeating of some code aspects and improve reporting mechanics. Plantuml will no longer be needed for the diagram portion in that implementation. In order to use `budgie`, you do **not** need to have plantuml for the other functions.

## Related Documents
- [STP Budget Package Description](docs/design_description.md)


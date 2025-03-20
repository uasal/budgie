from budgie.core import Budget
import yaml
import subprocess
from copy import deepcopy
import plantuml

class Plantuml_Writer:
    """
        Writer class for just making a basic edit an indicated 
        budgets yaml file for Plantuml to be able to display 
        it without any other additional edits yet.
    """

    def __init__(self, file, destination):
        
        self.file = file
        self.destination = destination

    def create_plantuml(file, destination):
        """

        Args:
            file (str): "path/file" to the yaml file you want to display
            destination (str): "path/file" to the output modified yaml
        """

        with open(file, 'r') as source:
            data = yaml.safe_load(source)
        #print(deepcopy(data))
        header = "@startyaml" + "\n"
        footer = "\n" + "@endyaml" + "\n"
        modified = deepcopy(data)

        """
        Better way to do this but this is just a placeholder / other tasks for moving away 
        from plantuml for the additional formatting features wanted.
        """
        with open(destination, 'w') as output:
            print(f"Writing plantuml format file from file:  {file}")
            yaml.dump(header, output)
            yaml.dump(modified, output)
            yaml.dump(footer, output)

        print(f"Outputting diagram generated from {destination}")
        cmd = f"java -jar plantuml.jar {destination}"
        plantuml_cmd = subprocess.run(cmd, capture_output=True, text=True)
        #print(plantuml_cmd)
        #print(plantuml_cmd.stdout)


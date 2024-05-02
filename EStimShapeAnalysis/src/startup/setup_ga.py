import os
import re

from startup import config


class PropertiesModifier:
    def __init__(self, properties_file_path):
        """
        Initializes the PropertiesModifier class.

        Args:
            properties_file_path: Path to the properties file to modify.
        """
        self.properties_file_path = properties_file_path

        # Reading the content of the properties file and storing it as a class field
        with open(self.properties_file_path, 'r') as properties_file:
            self.properties_content = properties_file.readlines()

    def replace_property(self, var_name, new_value):
        """
        Replaces a specific property in the properties file content.

        Args:
            var_name: The property name to replace (e.g., 'generator.png_path').
            new_value: The new value to assign to the property.
        """
        # Create the replacement string
        new_line = f"{var_name} = {new_value}"

        # Pattern to match lines starting with the property name
        pattern = re.compile(fr"{var_name}.*")

        # Find and replace the matching line
        for i, line in enumerate(self.properties_content):
            if pattern.match(line):
                self.properties_content[i] = new_line + "\n"
                break

    def save_changes(self):
        """
        Saves the modified content back to the properties file.
        """
        with open(self.properties_file_path, 'w') as properties_file:
            properties_file.writelines(self.properties_content)


class PathMaker:
    def __init__(self):
        """Initializes an empty list to hold paths."""
        self.paths = []

    def add_path(self, path):
        """
        Adds a new path to the list of paths.

        Args:
            path: A string representing the directory path to add.
        """
        self.paths.append(path)

    def generate(self):
        """
        Creates all paths in the list, including any necessary parent directories.
        """
        for path in self.paths:
            # Create the path along with any necessary parent directories
            os.makedirs(path, exist_ok=True)

        print("Paths generated successfully.")


def main():
    # Define the necessary versions directly
    version_ga = config.ga_database
    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.ga'
    stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_ga}/stimuli"
    stimuli_base_m = f"/home/m2_allen/Documents/stimuli/{version_ga}"
    r_ga_path = f"{stimuli_base_r}/ga"
    m_ga_path = f"{stimuli_base_m}/ga"
    r_pngs = f"{r_ga_path}/pngs"
    m_pngs = f"{m_ga_path}/pngs"

    # Create an instance of PropertiesModifier
    modifier = PropertiesModifier(xper_properties_file_path)
    # Modify specific properties
    modifier.replace_property("jdbc.url",
                              f"jdbc.url=jdbc:mysql://172.30.6.80/{version_ga}?rewriteBatchedStatements=true")
    modifier.replace_property("generator.png_path", r_pngs)
    modifier.replace_property("experiment.png_path", m_pngs)
    # Save changes
    modifier.save_changes()
    print("xper.properties.ga file modified successfully.")

    # Pathmaker
    pathmaker = PathMaker()
    pathmaker.add_path(r_pngs)

    pathmaker.generate()


if __name__ == "__main__":
    main()

import os
import re

from startup import config


def main():
    setup_ga_xper_properties()
    setup_nafc_xper_properties()
    setup_isogabor_xper_properties()

    update_version_shellscript()


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


class XperPropertiesModifier:
    '''
    A class to easily modify the properties in a xper.properties file.

    First init the class with the path to the xper.properties file.

    Then call the replace_property method with the property name and the new value on
    all the properties you want to change.

    Finally, call the save_changes method to save the changes back to the file.
    '''

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

    def replace_property(self, var_name: str, new_value: str):
        """
        Replaces a specific property in the properties file content.

        Args:
            var_name: The property name to replace (e.g., 'generator.png_path').
            new_value: The new value to assign to the property.
        """
        # Create the replacement string
        new_line = f"{var_name}={new_value}"

        # Pattern to match lines starting with the property name
        pattern = re.compile(fr"{var_name}.*")

        # Find and replace the matching line
        for i, line in enumerate(self.properties_content):
            if pattern.match(line):
                self.properties_content[i] = new_line + "\n"
                return
        raise ValueError(f"Property {var_name} not found in {self.properties_file_path}")

    def save_changes(self):
        """
        Saves the modified content back to the properties file.
        """
        with open(self.properties_file_path, 'w') as properties_file:
            properties_file.writelines(self.properties_content)


def setup_ga_xper_properties(r2_sftp="/run/user/1004/gvfs/sftp:host=172.30.6.80"):
    # Define the necessary versions directly
    version_ga = config.ga_database
    recording_computer_sftp = r2_sftp
    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.ga'
    # DB URL
    db_url = f"jdbc:mysql://172.30.6.80/{version_ga}?rewriteBatchedStatements=true"
    # STIM PATHS
    stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_ga}/stimuli"
    r_ga_path = f"{stimuli_base_r}/ga"
    generator_png_path = f"{r_ga_path}/pngs"
    experiment_png_path = f"{recording_computer_sftp}{r_ga_path}/pngs"
    generator_spec_path = f"{r_ga_path}/specs"

    # RFPLOT
    generator_rfplot_pngs = "/home/r2_allen/git/EStimShape/xper-train/stimuli/rfplot/pngs"
    experiment_rfplot_pngs = f"{recording_computer_sftp}{generator_rfplot_pngs}"
    rfplot_intan_path = f"/home/i2_allen/Documents/EStimShape/{version_ga}/rfPlot"

    # INTAN
    intan_path = f"/home/i2_allen/Documents/EStimShape/{version_ga}/ga"

    # Create an instance of PropertiesModifier
    modifier = XperPropertiesModifier(xper_properties_file_path)
    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
        "generator.png_path": generator_png_path,
        "experiment.png_path": experiment_png_path,
        "generator.spec_path": generator_spec_path,
        "rfplot.png_library_path_generator": generator_rfplot_pngs,
        "rfplot.png_library_path_experiment": experiment_rfplot_pngs,
        "rfplot.intan_path": rfplot_intan_path,
        "intan.default_save_path": intan_path,
    }
    # Replace properties using the dictionary
    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)
    # Save changes
    modifier.save_changes()
    print("xper.properties.ga file modified successfully.")
    # PathMaker
    pathmaker = PathMaker()
    pathmaker.add_path(generator_png_path)
    pathmaker.add_path(generator_spec_path)
    pathmaker.generate()


def setup_nafc_xper_properties(r2_sftp="/run/user/1004/gvfs/sftp:host=172.30.6.80"):
    # Define the necessary versions directly
    version_nafc = config.nafc_database
    recording_computer_sftp = r2_sftp

    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.procedural'
    # DB URL
    db_url = f"jdbc:mysql://172.30.6.80/{version_nafc}?rewriteBatchedStatements=true"

    # PATHS
    stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_nafc}/stimuli"
    r_nafc_path = f"{stimuli_base_r}/procedural"
    generator_png_path = f"{r_nafc_path}/pngs"
    experiment_png_path = f"{recording_computer_sftp}{r_nafc_path}/pngs"
    generator_spec_path = f"{r_nafc_path}/specs"
    generator_noisemap_path = generator_png_path
    experiment_noisemap_path = experiment_png_path

    version_ga = config.ga_database
    ga_stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_ga}/stimuli"
    r_ga_path = f"{ga_stimuli_base_r}/ga"
    ga_spec_path = f"{r_ga_path}/specs"

    # INTAN
    intan_path = f"/home/i2_allen/Documents/EStimShape/{version_nafc}/nafc"

    # Create an instance of PropertiesModifier
    modifier = XperPropertiesModifier(xper_properties_file_path)
    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
        "generator.png_path": generator_png_path,
        "experiment.png_path": experiment_png_path,
        "generator.spec_path": generator_spec_path,
        "generator.noisemap_path": generator_noisemap_path,
        "experiment.noisemap_path": experiment_noisemap_path,
        "ga.spec_path": ga_spec_path,
        "intan.default_save_path": intan_path,
    }

    # Replace properties using the dictionary
    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)
    # Save changes
    modifier.save_changes()

    print("xper.properties.procedural file modified successfully.")

    # PathMaker
    pathmaker = PathMaker()
    pathmaker.add_path(generator_png_path)
    pathmaker.add_path(generator_spec_path)
    pathmaker.add_path(generator_noisemap_path)
    pathmaker.generate()


def setup_isogabor_xper_properties(r2_sftp="/run/user/1004/gvfs/sftp:host=172.30.6.80"):
    # Define the necessary versions directly
    version_isogabor = config.isogabor_database
    recording_computer_sftp = r2_sftp
    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.isogabor'
    # DB URL
    db_url = f"jdbc:mysql://172.30.6.80/{version_isogabor}?rewriteBatchedStatements=true"

    modifier = XperPropertiesModifier(xper_properties_file_path)
    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
    }
    # Replace properties using the dictionary
    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)
    # Save changes
    modifier.save_changes()
    print("xper.properties.ga file modified successfully.")


def update_version_shellscript():
    # Retrieve versions from the config or define directly
    version_ga = config.ga_database
    version_isogabor = config.isogabor_database  # Replace with how you retrieve this information
    version_procedural = config.nafc_database  # Replace with how you retrieve this information

    # Path to the version file
    version_file_path = "/home/r2_allen/git/EStimShape/xper-train/shellScripts/version"

    # Reading and modifying the version file content
    with open(version_file_path, 'r') as version_file:
        version_content = version_file.read()

    # Replace VERSION_GA, VERSION_ISOGABOR, and VERSION_PROCEDURAL
    version_content = re.sub(r"VERSION_GA=.*", f"VERSION_GA={version_ga}", version_content)
    version_content = re.sub(r"VERSION_ISOGABOR=.*", f"VERSION_ISOGABOR={version_isogabor}", version_content)
    version_content = re.sub(r"VERSION_PROCEDURAL=.*", f"VERSION_PROCEDURAL={version_procedural}", version_content)

    # Writing the modified content back to the version file
    with open(version_file_path, 'w') as version_file:
        version_file.write(version_content)

    print("Version file updated successfully.")


if __name__ == "__main__":
    main()

import os
import re
from datetime import datetime
from src.startup import context


def main():
    setup_ga_xper_properties()
    setup_ga_dirs()

    setup_nafc_xper_properties()

    setup_isogabor_xper_properties()
    setup_isogabor_dirs()

    setup_twodvsthreed_xper_properties()
    setup_twodvsthreed_dirs()

    update_version_shellscript()


def make_path(path):
    """
    Adds a new path to the list of paths.

    Args:
        path: A string representing the directory path to add.
    """
    os.makedirs(path, exist_ok=True)
    if os.path.exists(path):
        print(f"Path {path} created.")
    else:
        print(f"Failed to create path {path}.")


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
    version_ga = context.ga_database
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
    intan_path = f"/home/i2_allen/Documents/EStimShape/{version_ga}"

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
    make_path(generator_png_path)
    make_path(generator_spec_path)


def setup_ga_dirs():
    make_path(context.java_output_dir)
    make_path(context.rwa_output_dir)
    make_path(context.eyecal_dir)


def setup_nafc_xper_properties(r2_sftp="/run/user/1004/gvfs/sftp:host=172.30.6.80"):
    # Define the necessary versions directly
    version_nafc = context.nafc_database
    recording_computer_sftp = r2_sftp

    # Get current date in YYMMDD format
    current_date = datetime.now().strftime("%y%m%d")

    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.procedural'
    # DB URL
    db_url = f"jdbc:mysql://172.30.6.80/{version_nafc}?rewriteBatchedStatements=true"

    # PATHS
    stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_nafc}/stimuli"
    r_nafc_path = f"{stimuli_base_r}/{current_date}/procedural"
    generator_png_path = f"{r_nafc_path}/pngs"
    experiment_png_path = f"{recording_computer_sftp}{r_nafc_path}/pngs"
    generator_spec_path = f"{r_nafc_path}/specs"
    generator_noisemap_path = generator_png_path
    generator_set_path = f"{stimuli_base_r}/{current_date}/sets"
    experiment_noisemap_path = experiment_png_path

    version_ga = context.ga_database
    ga_stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_ga}/stimuli"
    r_ga_path = f"{ga_stimuli_base_r}/ga"
    ga_spec_path = f"{r_ga_path}/specs"

    # INTAN
    intan_path = f"/home/i2_allen/Documents/EStimShape/{version_nafc}"

    # Create an instance of PropertiesModifier
    modifier = XperPropertiesModifier(xper_properties_file_path)
    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
        "generator.png_path": generator_png_path,
        "experiment.png_path": experiment_png_path,
        "generator.spec_path": generator_spec_path,
        "generator.noisemap_path": generator_noisemap_path,
        "generator.set_path": generator_set_path,
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

    # Create directories
    make_path(generator_png_path)
    make_path(generator_spec_path)
    make_path(generator_noisemap_path)
    make_path(generator_set_path)


def setup_isogabor_xper_properties(r2_sftp="/run/user/1004/gvfs/sftp:host=172.30.6.80"):
    # Define the necessary versions directly
    version_isogabor = context.isogabor_database
    recording_computer_sftp = r2_sftp
    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.isogabor'
    # DB URL
    db_url = f"jdbc:mysql://172.30.6.80/{version_isogabor}?rewriteBatchedStatements=true"

    intan_path = f"/home/i2_allen/Documents/EStimShape/{version_isogabor}"
    modifier = XperPropertiesModifier(xper_properties_file_path)
    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
        "intan.default_save_path": intan_path,
    }
    # Replace properties using the dictionary
    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)
    # Save changes
    modifier.save_changes()
    print("xper.properties.ga file modified successfully.")


def setup_isogabor_dirs():
    version_isogabor = context.isogabor_database
    isogabor_path = f"/home/r2_allen/Documents/EStimShape/{version_isogabor}"
    isogabor_parsed_spike_path = f"{isogabor_path}/parsed_spikes"
    make_path(isogabor_parsed_spike_path)


def setup_twodvsthreed_xper_properties(r2_sftp="/run/user/1004/gvfs/sftp:host=172.30.6.80"):
    # Define the necessary versions directly
    version_twodvsthreed = context.twodvsthreed_database
    version_ga = context.ga_database
    recording_computer_sftp = r2_sftp

    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.twodvsthreed'

    # DB URLs
    db_url = f"jdbc:mysql://172.30.6.80/{version_twodvsthreed}?rewriteBatchedStatements=true"
    ga_db_url = f"jdbc:mysql://172.30.6.80/{version_ga}?rewriteBatchedStatements=true"

    # PATHS
    stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_twodvsthreed}/stimuli"
    r_twodvsthreed_path = f"{stimuli_base_r}/twodvsthreed"

    # PNG and SPEC paths
    generator_png_path = f"{r_twodvsthreed_path}/pngs"
    experiment_png_path = f"{recording_computer_sftp}{r_twodvsthreed_path}/pngs"
    generator_spec_path = f"{r_twodvsthreed_path}/specs"

    # GA spec path
    ga_stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_ga}/stimuli"
    r_ga_path = f"{ga_stimuli_base_r}/ga"
    ga_spec_path = f"{r_ga_path}/specs"

    # Intan
    intan_path = f"/home/i2_allen/Documents/EStimShape/{version_twodvsthreed}"

    # Create an instance of PropertiesModifier
    modifier = XperPropertiesModifier(xper_properties_file_path)

    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
        "ga.jdbc.url": ga_db_url,
        "generator.png_path": generator_png_path,
        "experiment.png_path": experiment_png_path,
        "generator.spec_path": generator_spec_path,
        "ga.spec_path": ga_spec_path,
        "intan.default_save_path": intan_path,
    }

    # Replace properties using the dictionary
    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)

    # Save changes
    modifier.save_changes()
    print("xper.properties.twodvsthreed file modified successfully.")

    # Create necessary directories
    make_path(generator_png_path)
    make_path(generator_spec_path)


def setup_twodvsthreed_dirs():
    version_twodvsthreed = context.twodvsthreed_database
    twodvsthreed_path = f"/home/r2_allen/Documents/EStimShape/{version_twodvsthreed}"
    twodvsthreed_parsed_spike_path = f"{twodvsthreed_path}/parsed_spikes"
    make_path(twodvsthreed_parsed_spike_path)


def setup_twodthreedlightness_xper_properties(r2_sftp="/run/user/1004/gvfs/sftp:host=172.30.6.80"):
    # Define the necessary versions directly
    version_twodthreedlightness = context.twodthreedlightness_database
    version_ga = context.ga_database
    recording_computer_sftp = r2_sftp

    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.twodvsthreed'

    # DB URLs
    db_url = f"jdbc:mysql://172.30.6.80/{version_twodthreedlightness}?rewriteBatchedStatements=true"
    ga_db_url = f"jdbc:mysql://172.30.6.80/{version_ga}?rewriteBatchedStatements=true"

    # PATHS
    stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_twodthreedlightness}/stimuli"
    r_twodvsthreed_path = f"{stimuli_base_r}/twodvsthreed"

    # PNG and SPEC paths
    generator_png_path = f"{r_twodvsthreed_path}/pngs"
    experiment_png_path = f"{recording_computer_sftp}{r_twodvsthreed_path}/pngs"
    generator_spec_path = f"{r_twodvsthreed_path}/specs"

    # GA spec path
    ga_stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{version_ga}/stimuli"
    r_ga_path = f"{ga_stimuli_base_r}/ga"
    ga_spec_path = f"{r_ga_path}/specs"

    # Intan
    intan_path = f"/home/i2_allen/Documents/EStimShape/{version_twodthreedlightness}"

    # Create an instance of PropertiesModifier
    modifier = XperPropertiesModifier(xper_properties_file_path)

    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
        "ga.jdbc.url": ga_db_url,
        "generator.png_path": generator_png_path,
        "experiment.png_path": experiment_png_path,
        "generator.spec_path": generator_spec_path,
        "ga.spec_path": ga_spec_path,
        "intan.default_save_path": intan_path,
    }

    # Replace properties using the dictionary
    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)

    # Save changes
    modifier.save_changes()
    print("xper.properties.twodvsthreed file modified successfully.")

    # Create necessary directories
    make_path(generator_png_path)
    make_path(generator_spec_path)


def setup_twodvsthreed_dirs():
    version_twodthreedlightness = context.twodthreedlightness_database
    twodvsthreed_path = f"/home/r2_allen/Documents/EStimShape/{version_twodthreedlightness}"
    twodvsthreed_parsed_spike_path = f"{twodvsthreed_path}/parsed_spikes"
    make_path(twodvsthreed_parsed_spike_path)


def update_version_shellscript():
    # Retrieve versions from the config
    version_ga = context.ga_database
    version_isogabor = context.isogabor_database
    version_procedural = context.nafc_database
    version_twodvsthreed = context.twodvsthreed_database

    # Path to the version file
    version_file_path = "/home/r2_allen/git/EStimShape/xper-train/shellScripts/version"

    # Reading and modifying the version file content
    with open(version_file_path, 'r') as version_file:
        version_content = version_file.read()

    # Replace all version variables
    version_content = re.sub(r"VERSION_GA=.*", f"VERSION_GA={version_ga}", version_content)
    version_content = re.sub(r"VERSION_ISOGABOR=.*", f"VERSION_ISOGABOR={version_isogabor}", version_content)
    version_content = re.sub(r"VERSION_PROCEDURAL=.*", f"VERSION_PROCEDURAL={version_procedural}", version_content)
    version_content = re.sub(r"VERSION_TWODVSTHREED=.*", f"VERSION_TWODVSTHREED={version_twodvsthreed}",
                             version_content)

    # Writing the modified content back to the version file
    with open(version_file_path, 'w') as version_file:
        version_file.write(version_content)

    print("Version file updated successfully.")


if __name__ == "__main__":
    main()

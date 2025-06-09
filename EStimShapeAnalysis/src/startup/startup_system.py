import importlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import re
from datetime import datetime
import mysql.connector
from clat.util.connection import Connection
from src.pga.multi_ga_db_util import MultiGaDbUtil

# Import existing utilities instead of recreating them
from src.startup.setup_xper_properties_and_dirs import XperPropertiesModifier, make_path
from src.startup.db_factory import migrate_database, reset_internal_state

# Template constants
TEMPLATE_TYPE = 'test'
TEMPLATE_DATE = '250609'
TEMPLATE_LOCATION_ID = '0'

# Database connection constants
HOST = '172.30.6.80'
USER = 'xper_rw'
PASS = 'up2nite'


class ExperimentType(ABC):
    """Abstract base class for experiment types"""

    def __init__(self, type_name: str, date: str, location_id: str):
        self.type_name = type_name
        self.date = date
        self.location_id = location_id

    @abstractmethod
    def get_experiment_prefix(self) -> str:
        """Return the prefix used in database naming (e.g., 'ga', 'estimshape')"""
        pass

    def get_context_variable_name(self) -> str:
        """Return the variable name used in context.py (e.g., 'ga_database')"""
        return f"{self.get_experiment_prefix()}_database"

    @abstractmethod
    def get_version_variable_name(self) -> str:
        """Return the variable name used in version script (e.g., 'VERSION_GA')"""
        pass

    @abstractmethod
    def get_copy_data_tables(self) -> List[str]:
        """Return list of tables to copy data from template"""
        pass

    @abstractmethod
    def get_properties_file_path(self) -> str:
        """Return path to the properties file for this experiment"""
        pass

    @abstractmethod
    def get_properties_dict(self, r2_sftp: str) -> Dict[str, str]:
        """Return dictionary of properties to update"""
        pass

    @abstractmethod
    def create_directories(self) -> None:
        """Create necessary directories for this experiment"""
        pass

    def get_database_name(self) -> str:
        """Generate database name following naming convention"""
        return f"allen_{self.get_experiment_prefix()}_{self.type_name}_{self.date}_{self.location_id}"

    def get_template_database_name(self) -> str:
        """Generate template database name"""
        return f"allen_{self.get_experiment_prefix()}_{TEMPLATE_TYPE}_{TEMPLATE_DATE}_{TEMPLATE_LOCATION_ID}"

    def setup_database(self) -> None:
        """Create database from template - Template method"""
        source_config = {
            'host': HOST,
            'user': USER,
            'password': PASS,
            'database': self.get_template_database_name()
        }

        dest_config = {
            'host': HOST,
            'user': USER,
            'password': PASS,
            'database': self.get_database_name()
        }

        migrate_database(source_config, dest_config, copy_data_tables=self.get_copy_data_tables())

        try:
            reset_internal_state(dest_config)
        except Exception as e:
            print(f"Error resetting internal state for {self.get_database_name()}: {e}")

    def setup_properties(self, r2_sftp: str = "/run/user/1004/gvfs/sftp:host=172.30.6.80") -> None:
        """Setup properties file - Template method"""
        modifier = XperPropertiesModifier(self.get_properties_file_path())
        properties_dict = self.get_properties_dict(r2_sftp)

        for var_name, new_value in properties_dict.items():
            modifier.replace_property(var_name, new_value)

        modifier.save_changes()
        print(f"{self.get_properties_file_path()} file modified successfully.")


class GAExperiment(ExperimentType):
    """Genetic Algorithm experiment type"""

    def get_experiment_prefix(self) -> str:
        return "ga"

    def get_version_variable_name(self) -> str:
        return "VERSION_GA"

    def get_copy_data_tables(self) -> List[str]:
        return ["SystemVar", "InternalState", "GAVar"]

    def get_properties_file_path(self) -> str:
        return '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.ga'

    def get_properties_dict(self, r2_sftp: str) -> Dict[str, str]:
        db_name = self.get_database_name()
        stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{db_name}/stimuli"
        r_ga_path = f"{stimuli_base_r}/ga"

        return {
            "jdbc.url": f"jdbc:mysql://172.30.6.80/{db_name}?rewriteBatchedStatements=true",
            "generator.png_path": f"{r_ga_path}/pngs",
            "experiment.png_path": f"{r2_sftp}{r_ga_path}/pngs",
            "generator.spec_path": f"{r_ga_path}/specs",
            "rfplot.png_library_path_generator": "/home/r2_allen/git/EStimShape/xper-train/stimuli/rfplot/pngs",
            "rfplot.png_library_path_experiment": f"{r2_sftp}/home/r2_allen/git/EStimShape/xper-train/stimuli/rfplot/pngs",
            "rfplot.intan_path": f"/home/i2_allen/Documents/EStimShape/{db_name}/rfPlot",
            "intan.default_save_path": f"/home/i2_allen/Documents/EStimShape/{db_name}",
        }

    def create_directories(self) -> None:
        db_name = self.get_database_name()
        base_dir = f"/home/r2_allen/Documents/EStimShape/{db_name}"

        # GA-specific directories
        make_path(f"{base_dir}/stimuli/ga/pngs")
        make_path(f"{base_dir}/stimuli/ga/specs")
        make_path(f"{base_dir}/java_output")
        make_path(f"{base_dir}/rwa")
        make_path(f"{base_dir}/eyecal")
        make_path(f"{base_dir}/plots")
        make_path(f"{base_dir}/parsed_spikes")


class NAFCExperiment(ExperimentType):
    """NAFC/Procedural experiment type"""

    def get_experiment_prefix(self) -> str:
        return "estimshape"

    def get_context_variable_name(self) -> str:
        return "nafc_database"

    def get_version_variable_name(self) -> str:
        return "VERSION_PROCEDURAL"

    def get_copy_data_tables(self) -> List[str]:
        return ["SystemVar", "InternalState"]

    def get_properties_file_path(self) -> str:
        return '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.procedural'

    def get_properties_dict(self, r2_sftp: str) -> Dict[str, str]:
        db_name = self.get_database_name()
        current_date = datetime.now().strftime("%y%m%d")
        stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{db_name}/stimuli"
        r_nafc_path = f"{stimuli_base_r}/{current_date}/procedural"

        # GA paths for cross-reference
        ga_db_name = f"allen_ga_{self.type_name}_{self.date}_{self.location_id}"
        ga_spec_path = f"/home/r2_allen/Documents/EStimShape/{ga_db_name}/stimuli/ga/specs"

        return {
            "jdbc.url": f"jdbc:mysql://172.30.6.80/{db_name}?rewriteBatchedStatements=true",
            "generator.png_path": f"{r_nafc_path}/pngs",
            "experiment.png_path": f"{r2_sftp}{r_nafc_path}/pngs",
            "generator.spec_path": f"{r_nafc_path}/specs",
            "generator.noisemap_path": f"{r_nafc_path}/pngs",
            "generator.set_path": f"{stimuli_base_r}/{current_date}/sets",
            "experiment.noisemap_path": f"{r2_sftp}{r_nafc_path}/pngs",
            "ga.spec_path": ga_spec_path,
            "intan.default_save_path": f"/home/i2_allen/Documents/EStimShape/{db_name}",
        }

    def create_directories(self) -> None:
        db_name = self.get_database_name()
        current_date = datetime.now().strftime("%y%m%d")
        stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{db_name}/stimuli"

        make_path(f"{stimuli_base_r}/{current_date}/procedural/pngs")
        make_path(f"{stimuli_base_r}/{current_date}/procedural/specs")
        make_path(f"{stimuli_base_r}/{current_date}/sets")


class IsoGaborExperiment(ExperimentType):
    """IsoGabor experiment type"""

    def get_experiment_prefix(self) -> str:
        return "isogabor"

    def get_version_variable_name(self) -> str:
        return "VERSION_ISOGABOR"

    def get_copy_data_tables(self) -> List[str]:
        return ["SystemVar", "InternalState", "SinGain", "MonitorLin"]

    def get_properties_file_path(self) -> str:
        return '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.isogabor'

    def get_properties_dict(self, r2_sftp: str) -> Dict[str, str]:
        db_name = self.get_database_name()
        return {
            "jdbc.url": f"jdbc:mysql://172.30.6.80/{db_name}?rewriteBatchedStatements=true",
            "intan.default_save_path": f"/home/i2_allen/Documents/EStimShape/{db_name}",
        }

    def create_directories(self) -> None:
        db_name = self.get_database_name()
        base_dir = f"/home/r2_allen/Documents/EStimShape/{db_name}"

        make_path(f"{base_dir}/plots")
        make_path(f"{base_dir}/parsed_spikes")


class TwoDVsThreeDExperiment(ExperimentType):
    """2D vs 3D experiment type"""

    def get_experiment_prefix(self) -> str:
        return "twodvsthreed"

    def get_version_variable_name(self) -> str:
        return "VERSION_TWODVSTHREED"

    def get_copy_data_tables(self) -> List[str]:
        return ["SystemVar", "InternalState"]

    def get_properties_file_path(self) -> str:
        return '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.twodvsthreed'

    def get_properties_dict(self, r2_sftp: str) -> Dict[str, str]:
        db_name = self.get_database_name()
        stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{db_name}/stimuli"
        r_twodvsthreed_path = f"{stimuli_base_r}/twodvsthreed"

        # GA paths for cross-reference
        ga_db_name = f"allen_ga_{self.type_name}_{self.date}_{self.location_id}"
        ga_spec_path = f"/home/r2_allen/Documents/EStimShape/{ga_db_name}/stimuli/ga/specs"

        return {
            "jdbc.url": f"jdbc:mysql://172.30.6.80/{db_name}?rewriteBatchedStatements=true",
            "ga.jdbc.url": f"jdbc:mysql://172.30.6.80/{ga_db_name}?rewriteBatchedStatements=true",
            "generator.png_path": f"{r_twodvsthreed_path}/pngs",
            "experiment.png_path": f"{r2_sftp}{r_twodvsthreed_path}/pngs",
            "generator.spec_path": f"{r_twodvsthreed_path}/specs",
            "ga.spec_path": ga_spec_path,
            "intan.default_save_path": f"/home/i2_allen/Documents/EStimShape/{db_name}",
        }

    def create_directories(self) -> None:
        db_name = self.get_database_name()
        stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{db_name}/stimuli"

        make_path(f"{stimuli_base_r}/twodvsthreed/pngs")
        make_path(f"{stimuli_base_r}/twodvsthreed/specs")
        make_path(f"/home/r2_allen/Documents/EStimShape/{db_name}/plots")
        make_path(f"/home/r2_allen/Documents/EStimShape/{db_name}/parsed_spikes")


class ShuffleExperiment(ExperimentType):
    def get_experiment_prefix(self) -> str:
        return "shuffle"

    def get_version_variable_name(self) -> str:
        return "VERSION_SHUFFLE"

    def get_copy_data_tables(self) -> List[str]:
        return ["SystemVar", "InternalState"]

    def get_properties_file_path(self) -> str:
        return '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.shuffle'

    def get_properties_dict(self, r2_sftp: str) -> Dict[str, str]:
        db_name = self.get_database_name()
        stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{db_name}/stimuli"
        r_shuffle_path = f"{stimuli_base_r}/shuffle"

        # GA paths for cross-reference
        ga_db_name = f"allen_ga_{self.type_name}_{self.date}_{self.location_id}"
        ga_spec_path = f"/home/r2_allen/Documents/EStimShape/{ga_db_name}/stimuli/ga/specs"

        return {
            "jdbc.url": f"jdbc:mysql://172.30.6.80/{db_name}?rewriteBatchedStatements=true",
            "ga.jdbc.url": f"jdbc:mysql://172.30.6.80/{ga_db_name}?rewriteBatchedStatements=true",
            "generator.png_path": f"{r_shuffle_path}/pngs",
            "experiment.png_path": f"{r2_sftp}{r_shuffle_path}/pngs",
            "generator.spec_path": f"{r_shuffle_path}/specs",
            "ga.spec_path": ga_spec_path,
            "intan.default_save_path": f"/home/i2_allen/Documents/EStimShape/{db_name}",
        }

    def create_directories(self) -> None:
        db_name = self.get_database_name()
        stimuli_base_r = f"/home/r2_allen/Documents/EStimShape/{db_name}/stimuli"

        make_path(f"{stimuli_base_r}/twodvsthreed/pngs")
        make_path(f"{stimuli_base_r}/twodvsthreed/specs")
        make_path(f"/home/r2_allen/Documents/EStimShape/{db_name}/plots")
        make_path(f"/home/r2_allen/Documents/EStimShape/{db_name}/parsed_spikes")

class ExperimentManager:
    """Main manager class for handling experiment setup"""

    def __init__(self, type_name: str, date: str, location_id: str):
        self.type_name = type_name
        self.date = date
        self.location_id = location_id

        # Define the experiments in order
        self.experiments = [
            GAExperiment(type_name, date, location_id),
            NAFCExperiment(type_name, date, location_id),
            IsoGaborExperiment(type_name, date, location_id),
            TwoDVsThreeDExperiment(type_name, date, location_id),
            ShuffleExperiment(type_name, date, location_id),
        ]

    def setup_databases(self) -> None:
        """Setup all databases"""
        print("Setting up databases...")
        for experiment in self.experiments:
            print(f"Creating database for {experiment.__class__.__name__}")
            experiment.setup_database()

    def setup_properties_and_directories(self, r2_sftp: str = "/run/user/1004/gvfs/sftp:host=172.30.6.80") -> None:
        """Setup all properties files and create directories"""
        print("Setting up properties files and directories...")
        for experiment in self.experiments:
            print(f"Setting up {experiment.__class__.__name__}")
            experiment.setup_properties(r2_sftp)
            experiment.create_directories()

    def update_context_file(self) -> None:
        """Update the context.py file with new database names dynamically"""
        target_file = '/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/startup/context.py'

        # Build dynamic mapping of variable names to database names
        context_mapping = {exp.get_context_variable_name(): exp.get_database_name()
                           for exp in self.experiments}

        # Read the target file
        with open(target_file, 'r') as file:
            lines = file.readlines()

        # Update lines dynamically
        new_lines = []
        for line in lines:
            updated = False
            for var_name, db_name in context_mapping.items():
                if line.startswith(f"{var_name} ="):
                    new_lines.append(f'{var_name} = "{db_name}"\n')
                    updated = True
                    break

            if not updated:
                new_lines.append(line)

        # Write the modified content back to the file
        with open(target_file, 'w') as file:
            file.writelines(new_lines)

        print("Context file updated successfully.")

        # Reload the context module so changes take effect in current session
        try:
            from src.startup import context
            importlib.reload(context)
            print("Context module reloaded successfully.")
        except Exception as e:
            print(f"Warning: Could not reload context module: {e}")
            print("You may need to restart your Python session for context changes to take effect.")

    def update_version_shellscript(self) -> None:
        """Update the version shellscript file"""
        version_file_path = "/home/r2_allen/git/EStimShape/xper-train/shellScripts/version"

        # Get version mappings dynamically
        version_mapping = {exp.get_version_variable_name(): exp.get_database_name()
                           for exp in self.experiments}

        # Read and modify the version file
        with open(version_file_path, 'r') as version_file:
            version_content = version_file.read()

        # Replace version variables
        for var_name, db_name in version_mapping.items():
            version_content = re.sub(rf"{var_name}=.*", f"{var_name}={db_name}", version_content)

        with open(version_file_path, 'w') as version_file:
            version_file.write(version_content)

        print("Version file updated successfully.")

    def databases_exist(self) -> bool:
        """Check if all databases for this experiment set already exist"""
        try:
            # Connect to MySQL server
            conn = mysql.connector.connect(host=HOST, user=USER, password=PASS)
            cursor = conn.cursor()

            for experiment in self.experiments:
                db_name = experiment.get_database_name()
                cursor.execute(f"SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
                if not cursor.fetchone():
                    conn.close()
                    return False

            conn.close()
            return True

        except mysql.connector.Error as e:
            print(f"Database connection error: {e}")
            return False

    def switch_context_only(self) -> None:
        """Switch to existing experiment configuration without creating new databases"""
        print(f"Switching to existing experiment configuration...")

        # Update context file first (with reload)
        self.update_context_file()

        # Then setup properties and directories using the updated context
        self.setup_properties_and_directories()
        self.update_version_shellscript()

        print(f"Successfully switched context to:")
        for experiment in self.experiments:
            print(f"  {experiment.__class__.__name__}: {experiment.get_database_name()}")

    def full_setup(self) -> None:
        """Complete setup process with proper module reloading"""
        print(
            f"Starting full setup for experiment type: {self.type_name}, date: {self.date}, location: {self.location_id}")

        # Step 1: Setup databases
        self.setup_databases()

        # Step 2: Update context file and reload module BEFORE setting up properties
        self.update_context_file()

        # Step 3: Now setup properties and directories (using updated context)
        self.setup_properties_and_directories()

        # Step 4: Update version script
        self.update_version_shellscript()

        print("Full setup completed successfully!")

        # Print summary
        print("\nDatabase Summary:")
        for experiment in self.experiments:
            print(f"  {experiment.__class__.__name__}: {experiment.get_database_name()}")


def main():
    """Main function: prompts user, checks if databases exist, then either switches context or does full setup"""

    # Get user input (same as your current code)
    current_date = input("Enter the date yymmdd, press enter to default to current date: ").strip()
    if current_date == "":
        current_date = datetime.now().strftime("%y%m%d")

    type_name = input("Enter the type (e.g., train, test, exp): ").strip().lower()
    location_id = input("Enter the location ID: ").strip()

    # Create manager
    manager = ExperimentManager(type_name, current_date, location_id)

    # Check if databases exist and choose action
    if manager.databases_exist():
        print("Databases already exist. Switching context...")
        manager.switch_context_only()
    else:
        print("Databases don't exist. Creating new experiment setup...")
        manager.full_setup()


if __name__ == "__main__":
    main()

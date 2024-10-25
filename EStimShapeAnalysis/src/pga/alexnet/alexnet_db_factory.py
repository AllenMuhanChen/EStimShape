from datetime import datetime

from clat.util.connection import Connection

from src.pga.alexnet import alexnet_context
from src.startup.db_factory import create_db_from_template, check_if_exists
from src.startup.setup_xper_properties_and_dirs import XperPropertiesModifier, make_path

HOST = '172.30.6.80'
USER = 'xper_rw'
PASS = 'up2nite'
TEMPLATE_TYPE = 'test'
TEMPLATE_DATE = '241024'
TEMPLATE_LOCATION_ID = '0'


def main():
    # Get current date in YYMMDD format
    current_date = datetime.now().strftime("%y%m%d")

    # Prompt user for TYPE
    type = input("Enter the type (e.g., train, test, exp): ").strip().lower()

    # Prompt user for location ID
    location_id = input("Enter the location ID: ").strip()

    # Create GA database name
    ga_database = f"allen_alexnet_ga_{type}_{current_date}_{location_id}"

    # Create lighting database name
    lighting_database = f"allen_alexnet_lighting_{type}_{current_date}_{location_id}"

    # Create GA database
    create_db_from_template(f'allen_alexnet_ga_{TEMPLATE_TYPE}_{TEMPLATE_DATE}_{TEMPLATE_LOCATION_ID}',
                            ga_database,
                            ["InternalState", "GAVar"],
                            copy_structure_tables=[
                                "InternalState",
                                "GAVar",
                                "LineageGaInfo",
                                "StimGaInfo",
                                "UnitActivations",
                                "CurrentExperiments",
                                "StimSpec",
                                "StimPath"
                            ])

    # Create lighting database with necessary tables
    create_db_from_template(f'allen_alexnet_ga_{TEMPLATE_TYPE}_{TEMPLATE_DATE}_{TEMPLATE_LOCATION_ID}',
                            lighting_database,
                            [],
                            copy_structure_tables=[
                                "StimPath",
                                "StimSpec",
                                "UnitActivations"
                            ])

    # Add StimInstructions table to lighting database only
    try:
        conn = Connection(host=HOST, user=USER, password=PASS, database=lighting_database)
        conn.execute("""
        CREATE TABLE StimInstructions (
            stim_id BIGINT PRIMARY KEY,
            parent_id BIGINT,
            stim_type VARCHAR(20),
            texture_type VARCHAR(20),
            light_pos_x FLOAT,
            light_pos_y FLOAT,
            light_pos_z FLOAT,
            light_pos_w FLOAT,
            contrast DOUBLE
        )
        """)
        conn.mydb.commit()
    except:
        print("StimInstructions table already exists in the database.")

    # Update context file for GA database
    update_context_file(ga_database, lighting_database)
    setup_ga_xper_properties_and_dirs(ga_database)
    make_path(alexnet_context.java_output_dir)
    make_path(alexnet_context.rwa_output_dir)

    # Create directories for lighting experiment
    make_path(f"/home/r2_allen/Documents/EStimShape/{lighting_database}")
    setup_lighting_posthoc_xper_properties_and_dirs(lighting_database)


def setup_lighting_posthoc_xper_properties_and_dirs(lighting_database):
    version = lighting_database
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.alexnet.lightingposthoc'
    db_url = f"jdbc:mysql://172.30.6.80/{version}?rewriteBatchedStatements=true"
    estimshape_base = f"/home/r2_allen/Documents/EStimShape/{version}"
    stimuli_base_r = f"{estimshape_base}/stimuli"
    r_ga_path = f"{stimuli_base_r}/ga"
    generator_png_path = f"{r_ga_path}/pngs"
    generator_spec_path = f"{r_ga_path}/specs"
    modifier = XperPropertiesModifier(xper_properties_file_path)
    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
        "generator.png_path": generator_png_path,
        "generator.spec_path": generator_spec_path,
    }

    # Replace properties using the dictionary
    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)
    # Save changes
    modifier.save_changes()
    make_path(estimshape_base)
    make_path(generator_png_path)
    make_path(generator_spec_path)

def setup_ga_xper_properties_and_dirs(ga_database):
    version = ga_database
    # Define paths to the properties file and directories
    xper_properties_file_path = '/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.alexnet'
    # DB URL
    db_url = f"jdbc:mysql://172.30.6.80/{version}?rewriteBatchedStatements=true"
    # STIM PATHS
    estimshape_base = f"/home/r2_allen/Documents/EStimShape/{version}"
    stimuli_base_r = f"{estimshape_base}/stimuli"
    r_ga_path = f"{stimuli_base_r}/ga"
    generator_png_path = f"{r_ga_path}/pngs"
    generator_spec_path = f"{r_ga_path}/specs"

    modifier = XperPropertiesModifier(xper_properties_file_path)
    # ALL PROPERTIES to REPLACE:
    properties_dict = {
        "jdbc.url": db_url,
        "generator.png_path": generator_png_path,
        "generator.spec_path": generator_spec_path,
    }

    # Replace properties using the dictionary
    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)
    # Save changes
    modifier.save_changes()
    make_path(estimshape_base)
    make_path(generator_png_path)
    make_path(generator_spec_path)


def update_context_file(ga_database, lighting_database):
    target_file = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/pga/alexnet/alexnet_context.py"

    # Read the target file
    with open(target_file, 'r') as file:
        lines = file.readlines()

    # Prepare the new content
    new_lines = []
    for line in lines:
        if line.startswith("ga_database"):
            new_lines.append(f'ga_database = "{ga_database}"\n')
        elif line.startswith("lighting_database"):
            new_lines.append(f'lighting_database = "{lighting_database}"\n')
        elif line.startswith("image_path"):
            new_lines.append(f'image_path = "/home/r2_allen/Documents/EStimShape/{ga_database}/stimuli/ga/pngs"\n')
        elif line.startswith("java_output_dir"):
            new_lines.append(f'java_output_dir = "/home/r2_allen/Documents/EStimShape/{ga_database}/java_output"\n')
        elif line.startswith("rwa_output_dir"):
            new_lines.append(f'rwa_output_dir = "/home/r2_allen/Documents/EStimShape/{ga_database}/rwa"\n')
        else:
            new_lines.append(line)

    # Write the modified content back to the file
    with open(target_file, 'w') as file:
        file.writelines(new_lines)


if __name__ == '__main__':
    main()

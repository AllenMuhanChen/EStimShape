from asyncio import sleep
from datetime import datetime

from clat.util.connection import Connection

from src.pga.alexnet import alexnet_context
from src.pga.alexnet.onnx_parser import UnitIdentifier, LayerType
from src.startup.db_factory import create_db_from_template, check_if_exists
from src.startup.setup_xper_properties_and_dirs import XperPropertiesModifier, make_path

HOST = '172.30.6.80'
USER = 'xper_rw'
PASS = 'up2nite'
TEMPLATE_TYPE = 'exp'
TEMPLATE_DATE = '241031'
TEMPLATE_LOCATION_ID = '2'


def main():
    # Get current date in YYMMDD format
    current_date = input("Enter the date yymmdd, press enter to default to current date: ").strip().lower()
    if current_date == "":
        current_date = datetime.now().strftime("%y%m%d")

    # Prompt user for TYPE
    type = input("Enter the type (e.g., train, test, exp): ").strip().lower()


    # Prompt user for location ID
    # Prompt user for unit number
    while True:
        try:
            unit_num = int(input("Enter the Conv3 unit number: ").strip())
            if 1 <= unit_num <= 384:  # Conv3 has 384 units
                break
            print("Unit number must be between 1 and 384")
        except ValueError:
            print("Please enter a valid number")

    # Create unit identifier
    unit = UnitIdentifier(layer=LayerType.CONV3, unit=unit_num, x=7, y=7)
    location_id = unit.to_string()

    # Create GA database name
    ga_database = f"allen_alexnet_ga_{type}_{current_date}_{location_id}"

    contrast_database = f"allen_alexnet_contrast_{type}_{current_date}_{location_id}"

    # Create lighting database name
    lighting_database = f"allen_alexnet_lighting_{type}_{current_date}_{location_id}"


    # Create directories for lighting experiment
    make_path(f"/home/r2_allen/Documents/EStimShape/{ga_database}")
    make_path(f"/home/r2_allen/Documents/EStimShape/{lighting_database}")
    make_path(f"/home/r2_allen/Documents/EStimShape/{contrast_database}")

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
    setup_alexnet_xper_properties_and_dirs(ga_database, "ga")

    # Create contrast database with necessary tables
    create_db_from_template(f'allen_alexnet_contrast_{TEMPLATE_TYPE}_{TEMPLATE_DATE}_{TEMPLATE_LOCATION_ID}',
                            contrast_database,
                            [],
                            copy_structure_tables=[
                                "StimPath",
                                "StimSpec",
                                "StimInstructions",
                                "UnitActivations"
                            ])
    setup_alexnet_xper_properties_and_dirs(contrast_database, "contrastposthoc")

    # Create lighting database with necessary tables
    create_db_from_template(f'allen_alexnet_lighting_{TEMPLATE_TYPE}_{TEMPLATE_DATE}_{TEMPLATE_LOCATION_ID}',
                            lighting_database,
                            [],
                            copy_structure_tables=[
                                "StimPath",
                                "StimSpec",
                                "StimInstructions",
                                "UnitActivations",
                                "UnitContributions"
                            ])
    setup_alexnet_xper_properties_and_dirs(lighting_database, "lightingposthoc")


    # Update context file for GA database
    update_context_file(ga_database, lighting_database, contrast_database, unit)
    sleep(1)

    # Dirs specified only in context file
    make_path(alexnet_context.java_output_dir)
    make_path(alexnet_context.rwa_output_dir)

    make_path(alexnet_context.ga_plots_dir)
    make_path(alexnet_context.lighting_plots_dir)
    make_path(alexnet_context.contrast_plots_dir)






def setup_alexnet_xper_properties_and_dirs(database, analysis_type):
    """Setup properties for analysis databases (lighting or contrast)"""
    version = database
    xper_properties_file_path = f'/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.alexnet.{analysis_type}'
    db_url = f"jdbc:mysql://172.30.6.80/{version}?rewriteBatchedStatements=true"
    estimshape_base = f"/home/r2_allen/Documents/EStimShape/{version}"
    stimuli_base_r = f"{estimshape_base}/stimuli"
    plots_path = f"{estimshape_base}/plots"
    r_ga_path = f"{stimuli_base_r}/ga"
    generator_png_path = f"{r_ga_path}/pngs"
    generator_spec_path = f"{r_ga_path}/specs"

    modifier = XperPropertiesModifier(xper_properties_file_path)
    properties_dict = {
        "jdbc.url": db_url,
        "generator.png_path": generator_png_path,
        "generator.spec_path": generator_spec_path,
    }

    for var_name, new_value in properties_dict.items():
        modifier.replace_property(var_name, new_value)
    modifier.save_changes()

    make_path(estimshape_base)
    make_path(plots_path)
    make_path(generator_png_path)
    make_path(generator_spec_path)




def update_context_file(ga_database, lighting_database, contrast_database, unit):
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
        elif line.startswith("contrast_database"):
            new_lines.append(f'contrast_database = "{contrast_database}"\n')
        elif line.startswith("image_path"):
            new_lines.append(f'image_path = "/home/r2_allen/Documents/EStimShape/{ga_database}/stimuli/ga/pngs"\n')
        elif line.startswith("java_output_dir"):
            new_lines.append(f'java_output_dir = "/home/r2_allen/Documents/EStimShape/{ga_database}/java_output"\n')
        elif line.startswith("rwa_output_dir"):
            new_lines.append(f'rwa_output_dir = "/home/r2_allen/Documents/EStimShape/{ga_database}/rwa"\n')
        elif line.startswith("ga_plots_dir"):
            new_lines.append(f'ga_plots_dir = "/home/r2_allen/Documents/EStimShape/{ga_database}/plots"\n')
        elif line.startswith("lighting_plots_dir"):
            new_lines.append(f'lighting_plots_dir = "/home/r2_allen/Documents/EStimShape/{lighting_database}/plots"\n')
        elif line.startswith("contrast_plots_dir"):
            new_lines.append(f'contrast_plots_dir = "/home/r2_allen/Documents/EStimShape/{contrast_database}/plots"\n')
        elif line.startswith("unit_string"):
            new_lines.append(f'unit_string = "{unit}"\n')

        else:
            new_lines.append(line)

    # Write the modified content back to the file
    with open(target_file, 'w') as file:
        file.writelines(new_lines)


if __name__ == '__main__':
    main()

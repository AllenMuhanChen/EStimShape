from datetime import datetime

from src.startup import context
from src.startup.setup_xper_properties_and_dirs import (
    setup_ga_xper_properties,
    setup_nafc_xper_properties,
    setup_isogabor_xper_properties,
    setup_twodvsthreed_xper_properties,
    update_version_shellscript,
    make_path
)


def switch_context(*, type_name: str, date: str, location_id: str) -> None:
    """
    Switch the context files and properties to a different version.

    Args:
        type_name: Experiment type (e.g., 'train', 'test', 'exp')
        date: Date in YYMMDD format
        location_id: Location identifier
    """
    # Construct database names
    ga_database = f"allen_ga_{type_name}_{date}_{location_id}"
    nafc_database = f"allen_estimshape_{type_name}_{date}_{location_id}"
    isogabor_database = f"allen_isogabor_{type_name}_{date}_{location_id}"
    twodvsthreed_database = f"allen_twodvsthreed_{type_name}_{date}_{location_id}"

    # Update context file
    update_context_file(ga_database, nafc_database, isogabor_database, twodvsthreed_database)

    # Update properties files and create necessary directories
    update_properties_and_dirs(ga_database, nafc_database, isogabor_database, twodvsthreed_database)

    print(f"Successfully switched context to:")
    print(f"GA Database: {ga_database}")
    print(f"NAFC Database: {nafc_database}")
    print(f"IsoGabor Database: {isogabor_database}")
    print(f"2D vs 3D Database: {twodvsthreed_database}")


def update_context_file(ga_database, nafc_database, isogabor_database, twodvsthreed_database):
    """
    Update the context.py file with new database names and paths.
    """
    target_file = '/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/startup/context.py'

    # Read the target file
    with open(target_file, 'r') as file:
        lines = file.readlines()

    # Prepare the new content
    new_lines = []
    for line in lines:
        if line.startswith("ga_database ="):
            new_lines.append(f'ga_database = "{ga_database}"\n')
        elif line.startswith("nafc_database ="):
            new_lines.append(f'nafc_database = "{nafc_database}"\n')
        elif line.startswith("isogabor_database ="):
            new_lines.append(f'isogabor_database = "{isogabor_database}"\n')
        elif line.startswith("twodvsthreed_database ="):
            new_lines.append(f'twodvsthreed_database = "{twodvsthreed_database}"\n')
        else:
            new_lines.append(line)

    # Write the modified content back to the file
    with open(target_file, 'w') as file:
        file.writelines(new_lines)


def update_properties_and_dirs(ga_database, nafc_database, isogabor_database, twodvsthreed_database):
    """
    Update all properties files and create directories by using existing functions
    """
    # Directly modify the global context to use new values
    # No need to restore original values - we want the change to be permanent
    context.ga_database = ga_database
    context.nafc_database = nafc_database
    context.isogabor_database = isogabor_database
    context.twodvsthreed_database = twodvsthreed_database

    # The context module's values are now updated both in memory and in the file
    # Use existing functions to set up properties and directories
    setup_ga_xper_properties()
    setup_nafc_xper_properties()
    setup_isogabor_xper_properties()
    setup_twodvsthreed_xper_properties()
    update_version_shellscript()

    # Create additional required directories
    create_required_directories(ga_database, nafc_database, isogabor_database, twodvsthreed_database)


def create_required_directories(ga_database, nafc_database, isogabor_database, twodvsthreed_database):
    """
    Create any additional directories needed beyond what the setup functions create
    """
    # GA directories
    ga_base_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}"
    make_path(f"{ga_base_dir}/java_output")
    make_path(f"{ga_base_dir}/rwa")
    make_path(f"{ga_base_dir}/eyecal")


def main():
    """
    Main function to gather user input and switch context.
    """
    # Get current date in YYMMDD format
    date = input("Enter the date yymmdd, press enter to default to current date: ").strip().lower()
    if date == "":
        date = datetime.now().strftime("%y%m%d")

    # Prompt user for TYPE
    type_name = input("Enter the type (e.g., train, test, exp): ").strip().lower()

    # Prompt user for location ID
    location_id = input("Enter the location ID: ").strip()

    switch_context(type_name=type_name, date=date, location_id=location_id)


if __name__ == "__main__":
    main()
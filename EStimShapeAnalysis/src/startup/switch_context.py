from datetime import datetime

from src.startup import context, setup_xper_properties_and_dirs
from src.startup.db_factory import update_context_file
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
    setup_xper_properties_and_dirs.main()

    print(f"Successfully switched context to:")
    print(f"GA Database: {ga_database}")
    print(f"NAFC Database: {nafc_database}")
    print(f"IsoGabor Database: {isogabor_database}")
    print(f"2D vs 3D Database: {twodvsthreed_database}")




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
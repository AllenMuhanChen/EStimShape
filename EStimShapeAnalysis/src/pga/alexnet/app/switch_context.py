from datetime import datetime

from src.pga.alexnet.app.alexnet_db_factory import update_context_file, setup_alexnet_xper_properties_and_dirs


def switch_context(*, type: str, date: str, location_id: str) -> None:
    """
    Switch the context files and properties to a different version.

    Args:
        type: Experiment type (e.g., 'train', 'test', 'exp')
        date: Date in YYMMDD format
        location_id: Location identifier
    """
    # Construct database names
    ga_database = f"allen_alexnet_ga_{type}_{date}_{location_id}"
    lighting_database = f"allen_alexnet_lighting_{type}_{date}_{location_id}"
    contrast_database = f"allen_alexnet_contrast_{type}_{date}_{location_id}"

    # Update context file
    update_context_file(ga_database, lighting_database, contrast_database)

    # Update properties files for each type
    setup_alexnet_xper_properties_and_dirs(ga_database, "ga")
    setup_alexnet_xper_properties_and_dirs(contrast_database, "contrastposthoc")
    setup_alexnet_xper_properties_and_dirs(lighting_database, "lightingposthoc")

    print(f"Successfully switched context to:")
    print(f"GA Database: {ga_database}")
    print(f"Lighting Database: {lighting_database}")
    print(f"Contrast Database: {contrast_database}")

def main():
    date = input("Enter the date yymmdd, press enter to default to current date: ").strip().lower()
    if date == "":
        date = datetime.now().strftime("%y%m%d")

    # Prompt user for TYPE
    type = input("Enter the type (e.g., train, test, exp): ").strip().lower()

    # Prompt user for location ID
    location_id = input("Enter the location ID: ").strip()

    switch_context(type=type, date=date, location_id=location_id)


if __name__ == "__main__":
    main()
from clat.eyecal.params import EyeCalibrationParameters
from clat.util.connection import Connection
from src.startup import config


def main():
    ga_db = Connection(config.ga_database)
    dest_db_names = [config.nafc_database, config.isogabor_database]
    dest_dbs = [Connection(dest_db_name) for dest_db_name in dest_db_names]
    params = EyeCalibrationParameters.read_params(ga_db)
    for dest_db in dest_dbs:
        params.write_params(dest_db)

if __name__ == "__main__":
    main()
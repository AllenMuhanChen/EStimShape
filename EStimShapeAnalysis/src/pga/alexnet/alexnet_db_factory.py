from datetime import datetime

from src.startup.db_factory import create_db_from_template, prompt_name


def main():
    database = "allen_alexnet_ga_dev_241021_0"

    create_db_from_template(f'allen_ga_test_241017_0',
                            database,
                            [
                                "InternalState",
                                "GAVar"],
                            copy_structure_tables=
                            ["InternalState",
                             "GAVar",
                             "LineageGaInfo",
                             "StimGaInfo",
                             "ChannelResponses",
                             "CurrentExperiments"]
                            )

    # update_config_file(ga_database, nafc_database, isogabor_database)


if __name__ == '__main__':
    main()

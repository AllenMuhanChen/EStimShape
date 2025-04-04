import mysql.connector

from src.startup.db_factory import migrate_database

# Database connection settings
HOST = '172.30.6.80'
USER = 'xper_rw'
PASS = 'up2nite'

# Set your source and destination database names here
SOURCE_DB = "allen_twodvsthreed_exp_250403_0"
DEST_DB = "allen_twodthreedlightness_exp_250403_0"

# List the tables you want to copy data from (empty list means structure only)
COPY_DATA_TABLES = ["SystemVar", "InternalState"]


def main():
    try:
        source_config = {
            'host': HOST,
            'user': USER,
            'password': PASS,
            'database': SOURCE_DB
        }

        dest_config = {
            'host': HOST,
            'user': USER,
            'password': PASS,
            'database': DEST_DB
        }

        # Perform the migration
        migrate_database(source_config, dest_config, copy_data_tables=COPY_DATA_TABLES)
        print(f"\nDatabase copied successfully!")
        print(f"Source: {SOURCE_DB}")
        print(f"Destination: {DEST_DB}")
        if COPY_DATA_TABLES:
            print("Tables copied with data:", ", ".join(COPY_DATA_TABLES))

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    main()
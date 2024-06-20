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

    copy_rfinfo_table(config.ga_database, config.nafc_database, ga_db)

def copy_rfinfo_table(source_schema: str, target_schema: str, conn: Connection):
    """
    Copy the contents of the RFInfo table from one database schema to another.

    Parameters:
    - source_schema: The name of the source schema.
    - target_schema: The name of the target schema.
    - conn: The Connection object to the database.
    """
    # Define the query to fetch data from the source schema
    fetch_query = f"SELECT * FROM {source_schema}.RFInfo"

    # Execute the fetch query
    conn.execute(fetch_query)
    rfinfo_data = conn.fetch_all()

    if not rfinfo_data:
        print("No data found in the source schema.")
        return

    # Define the insert query for the target schema
    insert_query = f"""
    INSERT INTO {target_schema}.RFInfo (tstamp, info, channel)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
    info = VALUES(info),
    channel = VALUES(channel)
    """

    # Insert the fetched data into the target schema
    for row in rfinfo_data:
        conn.execute(insert_query, row)

    print(f"Copied {len(rfinfo_data)} rows from {source_schema}.RFInfo to {target_schema}.RFInfo")




if __name__ == "__main__":
    main()
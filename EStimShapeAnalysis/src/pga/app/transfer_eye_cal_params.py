from clat.eyecal.params import EyeCalibrationParameters
from clat.util.connection import Connection
from src.startup import context
from typing import List

def main():
    ga_db = Connection(context.ga_database)
    dest_db_names = [context.nafc_database, context.isogabor_database, context.twodvsthreed_database]
    dest_dbs = [Connection(dest_db_name) for dest_db_name in dest_db_names]

    # Write calibration parameters
    params = EyeCalibrationParameters.read_params(ga_db)
    for dest_db in dest_dbs:
        params.write_params(dest_db)

    # Define tables to copy
    tables_to_copy = ["RFInfo", "RFObjectData", "ClusterInfo"]  # Add more table names to this list as needed

    # Copy tables to each destination database
    for dest_db_name in dest_db_names:
        copy_table_data(context.ga_database, dest_db_name, tables_to_copy, ga_db)

def check_table_exists(conn: Connection, schema: str, table: str) -> bool:
    """
    Check if a table exists in the specified schema.

    Parameters:
    - conn: The database connection
    - schema: Database schema name
    - table: Table name to check

    Returns:
    - bool: True if table exists, False otherwise
    """
    query = """
    SELECT COUNT(*)
    FROM information_schema.tables 
    WHERE table_schema = %s 
    AND table_name = %s
    """
    conn.execute(query, (schema, table))
    result = conn.fetch_one()
    return result > 0


def copy_table_data(source_schema: str, target_schema: str, table_names: List[str], conn: Connection) -> None:
    """
    Copy multiple tables from one schema to another.

    Parameters:
    - source_schema: The name of the source schema
    - target_schema: The name of the target schema
    - table_names: List of table names to copy
    - conn: The Connection object to the database
    """
    for table_name in table_names:
        # Check if table exists in source schema
        if not check_table_exists(conn, source_schema, table_name):
            print(f"Warning: Table {table_name} does not exist in source schema {source_schema}")
            continue

        # Check if table exists in target schema
        if not check_table_exists(conn, target_schema, table_name):
            print(f"Warning: Table {table_name} does not exist in target schema {target_schema}")
            continue

        try:
            # Get the table structure to ensure we copy all columns
            conn.execute(f"SHOW COLUMNS FROM {source_schema}.{table_name}")
            columns = [row[0] for row in conn.fetch_all()]
            columns_str = ", ".join(columns)

            # Fetch data from source
            fetch_query = f"SELECT {columns_str} FROM {source_schema}.{table_name}"
            conn.execute(fetch_query)
            table_data = conn.fetch_all()

            if not table_data:
                print(f"No data found in {source_schema}.{table_name}")
                continue

            # Prepare the insert query
            placeholders = ", ".join(["%s"] * len(columns))
            insert_query = f"""
            INSERT INTO {target_schema}.{table_name} ({columns_str})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE
            {", ".join(f"{col} = VALUES({col})" for col in columns)}
            """

            # Insert data into target
            for row in table_data:
                conn.execute(insert_query, row)

            print(
                f"Successfully copied {len(table_data)} rows from {source_schema}.{table_name} to {target_schema}.{table_name}")

        except Exception as e:
            print(f"Error copying table {table_name}: {str(e)}")




if __name__ == "__main__":
    main()
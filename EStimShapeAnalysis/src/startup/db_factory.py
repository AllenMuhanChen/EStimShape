import mysql.connector

from clat.util.connection import Connection
from pga.multi_ga_db_util import MultiGaDbUtil

HOST = '172.30.6.80'
USER = 'xper_rw'
PASS = 'up2nite'


def main():
    ga_database = "allen_estimshape_ga_test_240508"
    nafc_database = "allen_estimshape_test_240508"
    isogabor_database = "allen_isogabor_test_240508"

    # GA Database
    create_db_from_template('allen_estimshape_ga_dev_240207',
                            ga_database,
                            [
                                "SystemVar",
                                "InternalState",
                                "GAVar"])

    # NAFC Database
    create_db_from_template("allen_estimshape_train_231211",
                            nafc_database,
                            [
                                "SystemVar",
                                "InternalState"])

    # ISOGABOR Database
    create_db_from_template("allen_isogabor_dev_240322",
                            isogabor_database,
                            [
                                "SystemVar",
                                "InternalState",
                                "SinGain",
                                "MonitorLin"]
                            )


def create_db_from_template(source_db_name, dest_db_name, copy_data_tables):
    '''
    Create a new database from a template database
    :param source_db_name: The name of the database to copy from
    :param dest_db_name: The name of the new database
    :param copy_data_tables: A list of tables to copy data from

    all other tables not listed in copy_data_tables will only have structure copied.
    '''
    source_ga_db_config = {
        'host': HOST,
        'user': USER,
        'password': PASS,
        'database': source_db_name
    }

    dest_ga_db_config = {
        'host': HOST,
        'user': USER,
        'password': PASS,
        'database': dest_db_name
    }

    migrate_database(source_ga_db_config, dest_ga_db_config, copy_data_tables=copy_data_tables)

    reset_internal_state(dest_ga_db_config)


def replace_xml_in_table(connection):
    # XML string with the specified content and formatting
    # the weird spacing here is to get it to match the formatting of the existing XML strings
    xml_string = \
        """<GenerationInfo>
  <genId>0</genId>
  <taskCount>0</taskCount>
  <stimPerLinCount>0</stimPerLinCount>
  <repsPerStim>1</repsPerStim>
  <stimPerTrial>1</stimPerTrial>
  <useStereoRenderer>false</useStereoRenderer>
</GenerationInfo>"""

    cursor = connection.cursor()

    # Delete any existing row with the same identifiers
    delete_query = """
        DELETE FROM InternalState WHERE name = %s AND arr_ind = %s
        """
    cursor.execute(delete_query, ('task_to_do_gen_ready', 0))

    # Define the insertion query
    insert_query = """
        INSERT INTO InternalState (name, arr_ind, val)
        VALUES (%s, %s, %s)
        """

    # Execute the insertion query
    cursor.execute(insert_query, ('task_to_do_gen_ready', 0, xml_string))

    connection.commit()


def reset_internal_state(dest_ga_db_config):
    reset_task_to_do_ga_and_gen_ready(dest_ga_db_config)
    reset_task_to_do_gen_ready(dest_ga_db_config)


def reset_task_to_do_ga_and_gen_ready(dest_ga_db_config):
    # reset multi ga internal state
    conn = Connection(dest_ga_db_config['database'], dest_ga_db_config['user'], dest_ga_db_config['password'],
                      dest_ga_db_config['host'])
    db_util = MultiGaDbUtil(conn)
    db_util.update_ready_gas_and_generations_info(conn, 0)


def reset_task_to_do_gen_ready(dest_ga_db_config):
    # reset
    # Establish a connection to the destination database
    connection = mysql.connector.connect(**dest_ga_db_config)
    replace_xml_in_table(connection)
    connection.close()


def get_all_tables(cursor):
    # Fetch all table names from the source database
    cursor.execute("SHOW TABLES")
    return [table[0] for table in cursor.fetchall()]


def create_table_structure(cursor, table_name):
    # Fetch the table's CREATE TABLE statement from the source database
    cursor.execute(f"SHOW CREATE TABLE {table_name}")
    result = cursor.fetchone()

    if result:
        return result[1]
    else:
        raise ValueError(f"Table {table_name} does not exist or could not be fetched")


def copy_data(source_cursor, dest_cursor, table_name):
    # Fetch all rows from the source table
    source_cursor.execute(f"SELECT * FROM {table_name}")
    rows = source_cursor.fetchall()

    if rows:
        # Create a comma-separated placeholder string
        placeholders = ", ".join(["%s"] * len(rows[0]))

        # Create an insertion query
        insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"

        # Insert data into the destination table
        dest_cursor.executemany(insert_query, rows)


def database_exists(cursor, db_name):
    # Check if a database exists by querying the information schema
    cursor.execute(f"SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '{db_name}'")
    return cursor.fetchone() is not None


def recreate_database(cursor, db_name):
    cursor.execute(f"DROP DATABASE {db_name}")
    cursor.execute(f"CREATE DATABASE {db_name}")


def migrate_database(source_config, dest_config, copy_data_tables=[]):
    # Connect to the source database
    source_conn = mysql.connector.connect(**source_config)
    source_cursor = source_conn.cursor()

    # Connect to the MySQL server (not a specific database) for the destination
    dest_server_config = {key: value for key, value in dest_config.items() if key != 'database'}
    dest_server_conn = mysql.connector.connect(**dest_server_config)
    dest_server_cursor = dest_server_conn.cursor()

    # Check if the destination database exists
    dest_db_name = dest_config['database']
    if database_exists(dest_server_cursor, dest_db_name):
        response = input(
            f"The database '{dest_db_name}' already exists. Do you want to recreate it? (yes/no): ").strip().lower()
        if response == 'yes':
            recreate_database(dest_server_cursor, dest_db_name)
        elif response == 'no':
            print("Operation canceled.")
            source_conn.close()
            dest_server_conn.close()
            return
        else:
            print("Invalid response. Operation canceled.")
            source_conn.close()
            dest_server_conn.close()
            return
    else:
        dest_server_cursor.execute(f"CREATE DATABASE {dest_db_name}")

    # Connect to the destination database
    dest_conn = mysql.connector.connect(**dest_config)
    dest_cursor = dest_conn.cursor()

    # Get all tables in the source database
    all_tables = get_all_tables(source_cursor)

    # Copy tables
    for table in all_tables:
        create_table_sql = create_table_structure(source_cursor, table)
        dest_cursor.execute(create_table_sql)

        # Copy data if the table is specified in copy_data_tables
        if table in copy_data_tables:
            copy_data(source_cursor, dest_cursor, table)

    # Commit changes and close connections
    dest_conn.commit()
    source_conn.close()
    dest_conn.close()
    dest_server_conn.close()


# Example usage:


if __name__ == '__main__':
    main()

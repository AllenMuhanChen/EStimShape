import mysql.connector
from mysql.connector import Error
import sys


def create_connection(host_name, user_name, user_password, db_name=None):
    """Create a database connection to MySQL server"""
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        print("Connection to MySQL successful")
    except Error as e:
        print(f"The error '{e}' occurred")
        sys.exit(1)
    return connection


def create_database(connection, db_name):
    """Create a database in MySQL"""
    cursor = connection.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database {db_name} created successfully")
    except Error as e:
        print(f"The error '{e}' occurred")
    finally:
        cursor.close()


def execute_query(connection, query, description="Query"):
    """Execute a query in MySQL"""
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print(f"{description} executed successfully")
        return True
    except Error as e:
        print(f"Error in {description}: {e}")
        return False
    finally:
        cursor.close()


def main():
    # Configuration - Replace with your actual MySQL credentials
    host = "172.30.6.61"
    user = "xper_rw"
    password = "up2nite"
    db_name = "allen_data_repository"

    # Create a connection without specifying a database
    connection = create_connection(host, user, password)

    # Create the database
    create_database(connection, db_name)

    # Reconnect to the newly created database
    connection.close()
    connection = create_connection(host, user, password, db_name)

    # Create Sessions table for grouping experiments conducted on the same day
    create_sessions_table = """
    CREATE TABLE IF NOT EXISTS Sessions (
        session_id VARCHAR(10) PRIMARY KEY,
        session_date DATE NOT NULL,
        location VARCHAR(255)
    );
    """
    execute_query(connection, create_sessions_table, "Sessions table creation")

    # Create ReceptiveFieldInfo table linked to Sessions
    create_rf_info_table = """
    CREATE TABLE IF NOT EXISTS ReceptiveFieldInfo (
        session_id VARCHAR(10),
        channel VARCHAR(255),
        radius FLOAT,
        x FLOAT,
        y FLOAT,
        PRIMARY KEY (session_id, channel),
        FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_rf_info_table, "ReceptiveFieldInfo table creation")

    # Create Experiments table with session_id foreign key
    create_experiments_table = """
    CREATE TABLE IF NOT EXISTS Experiments (
        experiment_id VARCHAR(255) PRIMARY KEY,
        session_id VARCHAR(10) NOT NULL,
        experiment_name VARCHAR(255) NOT NULL,
        database_source VARCHAR(255),
        FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_experiments_table, "Experiments table creation")

    # Create ClusterInfo table
    create_cluster_info_table = """
    CREATE TABLE IF NOT EXISTS ClusterInfo (
        experiment_id VARCHAR(255),
        cluster_id VARCHAR(255),
        channel VARCHAR(255),
        gen_id INT,
        PRIMARY KEY (experiment_id, cluster_id, channel, gen_id),
        FOREIGN KEY (experiment_id) REFERENCES Experiments(experiment_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_cluster_info_table, "ClusterInfo table creation")

    # StimExperimentMapping becomes the central table for all stimuli
    create_stim_experiment_mapping_table = """
    CREATE TABLE IF NOT EXISTS StimExperimentMapping (
        stim_id BIGINT,
        experiment_id VARCHAR(255),
        PRIMARY KEY (stim_id, experiment_id),
        FOREIGN KEY (experiment_id) REFERENCES Experiments(experiment_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_stim_experiment_mapping_table, "StimExperimentMapping table creation")

    # Create TaskStimMapping table with reference to StimExperimentMapping
    create_task_stim_mapping_table = """
    CREATE TABLE IF NOT EXISTS TaskStimMapping (
        task_id BIGINT,
        stim_id BIGINT,
        PRIMARY KEY (task_id, stim_id),
        FOREIGN KEY (stim_id) REFERENCES StimExperimentMapping(stim_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_task_stim_mapping_table, "TaskStimMapping table creation")

    # Create Epochs table with foreign key to TaskStimMapping
    create_epochs_table = """
    CREATE TABLE IF NOT EXISTS Epochs (
        task_id BIGINT PRIMARY KEY,
        epoch_start FLOAT NOT NULL,
        epoch_end FLOAT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES TaskStimMapping(task_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_epochs_table, "Epochs table creation")

    # Create RawSpikeResponses table with foreign key to TaskStimMapping
    create_raw_spike_responses_table = """
    CREATE TABLE IF NOT EXISTS RawSpikeResponses (
        task_id BIGINT,
        channel_id VARCHAR(255),
        tstamps TEXT,  -- Stored as comma-separated list of timestamps
        response_rate FLOAT,
        PRIMARY KEY (task_id, channel_id),
        FOREIGN KEY (task_id) REFERENCES TaskStimMapping(task_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_raw_spike_responses_table, "RawSpikeResponses table creation")

    # Create WindowSortedResponses table with foreign key to TaskStimMapping
    create_window_sorted_responses_table = """
    CREATE TABLE IF NOT EXISTS WindowSortedResponses (
        task_id BIGINT,
        unit_id VARCHAR(255),
        tstamps TEXT,  -- Stored as comma-separated list of timestamps
        response_rate FLOAT,
        PRIMARY KEY (task_id, unit_id),
        FOREIGN KEY (task_id) REFERENCES TaskStimMapping(task_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_window_sorted_responses_table, "WindowSortedResponses table creation")

    # Create BackedUpExperiments table to track backups
    create_backed_up_experiments_table = """
    CREATE TABLE IF NOT EXISTS BackedUpExperiments (
        experiment_id VARCHAR(255),
        directory VARCHAR(500),
        PRIMARY KEY (experiment_id, directory),
        FOREIGN KEY (experiment_id) REFERENCES Experiments(experiment_id) ON DELETE CASCADE
    );
    """
    execute_query(connection, create_backed_up_experiments_table, "BackedUpExperiments table creation")


    print("All tables created successfully")
    connection.close()


if __name__ == "__main__":
    main()
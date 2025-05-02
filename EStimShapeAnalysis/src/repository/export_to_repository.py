import pandas as pd
import xmltodict
import datetime
from clat.util.connection import Connection
from typing import Tuple, Dict


def export_to_repository(df: pd.DataFrame, db_name: str, exp_name: str):
    repo_conn = Connection("allen_data_repository")
    to_export_conn = Connection(db_name)

    # session ID
    session_id, date = read_session_id_from_db(db_name)
    write_session_to_db(repo_conn, session_id, date)

    # RF INFO
    rf_info = read_rf_info(to_export_conn)
    write_rf_info_to_db(repo_conn, session_id, rf_info)

    # Experiments
    experiment_id = f"{session_id}_{exp_name}"
    write_experiment_to_db(repo_conn, experiment_id, session_id, exp_name, db_name)

    # ClusterInfo
    cluster_info = read_cluster_info(to_export_conn)
    write_cluster_info_to_db(repo_conn, experiment_id, cluster_info)

    # Stim Ids and Task Stim Mappings
    stim_task_mapping = read_stim_task_mapping(df)
    write_stim_experiment_mapping(repo_conn, experiment_id, stim_task_mapping)
    write_task_stim_mapping(repo_conn, stim_task_mapping)

    # Raw Spike Responses


    # IsoGaborStimInfo


    print(f"Export complete for {db_name} to repository database.")


def read_session_id_from_db(db_name: str) -> Tuple[str, datetime.date]:
    """
    Extract session ID and date from database name in the format "allen_expname_type_date_locationId".
    Returns the "date_locationId" as the session ID and the date as a datetime.date object.

    Example:
        "allen_isogabor_exp_250427_0" -> ("250427_0", datetime.date(2025, 4, 27))

    Args:
        db_name: Database name string

    Returns:
        Tuple of (session_id, date) where:
            - session_id is a string in the format "date_locationId"
            - date is a datetime.date object
    """
    # Split the database name by underscores
    parts = db_name.split('_')

    # The session ID components are the last two elements in the split result
    if len(parts) >= 2:
        date_str = parts[-2]
        location_id = parts[-1]
        session_id = f"{date_str}_{location_id}"

        # Convert the date string to a datetime.date object
        # Date format expected: YYMMDD (e.g., 250427 for April 27, 2025)
        if len(date_str) == 6:
            year = int("20" + date_str[0:2])  # Assuming 20xx for the year
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            date_obj = datetime.date(year, month, day)
            return (session_id, date_obj)
        else:
            raise ValueError(f"Date format in database name '{db_name}' is not the expected YYMMDD format")
    else:
        raise ValueError(f"Database name '{db_name}' does not follow the expected format")


def write_session_to_db(target_conn: Connection, session_id: str, date: datetime.date) -> str:
    """
    Write session information to the Sessions table.
    If the session already exists, returns its ID, otherwise creates a new session record.

    Args:
        target_conn: Connection to the target repository database
        session_id: Session ID string to use as the primary key
        date: Session date as a datetime.date object

    Returns:
        session_id: The session ID (which is the primary key in this schema)
    """
    # Format date for database (SQL date format)
    formatted_date = date.isoformat()

    # Check if session already exists
    query = "SELECT session_id FROM Sessions WHERE session_id = %s"
    params = (session_id,)
    target_conn.execute(query, params)
    result = target_conn.fetch_all()

    if result:
        # Session exists, return its ID
        return session_id

    # Create new session
    insert_query = "INSERT INTO Sessions (session_id, session_date, location) VALUES (%s, %s, NULL)"
    target_conn.execute(insert_query, (session_id, formatted_date))

    return session_id


def read_rf_info(conn: Connection) -> Dict[str, Dict[str, float]]:
    """
    Read RF information from the RFInfo table.
    For each channel, get the info associated with the highest timestamp.

    Args:
        conn: Connection to the database containing RFInfo table

    Returns:
        Dictionary mapping channel names to RF info dictionaries
    """
    # Get all unique channels
    conn.execute("SELECT DISTINCT channel FROM RFInfo WHERE channel IS NOT NULL")
    channels = [row[0] for row in conn.fetch_all()]

    rf_data = {}

    # For each channel, get the info with the highest timestamp
    for channel in channels:
        query = """
        SELECT info FROM RFInfo 
        WHERE channel = %s 
        ORDER BY tstamp DESC 
        LIMIT 1
        """
        conn.execute(query, (channel,))
        result = conn.fetch_all()

        if result and result[0][0]:
            # Parse the JSON info field
            info_str = result[0][0]
            info_dict = xmltodict.parse(info_str)

            # Extract the relevant RF parameters
            rf_info = {
                'radius': info_dict['RFInfo']['radius'],
                'x': info_dict['RFInfo']['center']['x'],
                'y': info_dict['RFInfo']['center']['y'],
            }

            rf_data[channel] = rf_info
            print(f"Found RF info for channel {channel}: {rf_info}")

    return rf_data


def write_rf_info_to_db(repo_conn: Connection, session_id: str, rf_data: Dict[str, Dict[str, float]]):
    """
    Write RF information to the ReceptiveFieldInfo table in the repository.

    Args:
        repo_conn: Connection to the repository database
        session_id: Session ID (primary key in Sessions table)
        rf_data: Dictionary mapping channel names to RF info dictionaries
    """
    for channel, rf_info in rf_data.items():
        query = """
        INSERT INTO ReceptiveFieldInfo (session_id, channel, radius, x, y)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE radius = %s, x = %s, y = %s
        """

        radius = rf_info.get('radius', 0.0)
        x = rf_info.get('x', 0.0)
        y = rf_info.get('y', 0.0)

        params = (
            session_id, channel, radius, x, y,
            radius, x, y
        )

        repo_conn.execute(query, params)
        print(f"Saved RF info for channel {channel} to repository")


def write_experiment_to_db(repo_conn: Connection, experiment_id: str, session_id: str,
                           experiment_name: str, database_source: str) -> str:
    """
    Write experiment information to the Experiments table.

    Args:
        repo_conn: Connection to the repository database
        experiment_id: Experiment ID string (e.g., "250427_0_isogabor")
        session_id: Session ID string (e.g., "250427_0")
        experiment_name: Name of the experiment (e.g., "Isogabor Experiment")
        database_source: Source database name

    Returns:
        experiment_id: The experiment ID
    """
    # Check if experiment already exists
    query = "SELECT experiment_id FROM Experiments WHERE experiment_id = %s"
    params = (experiment_id,)
    repo_conn.execute(query, params)
    result = repo_conn.fetch_all()

    if result:
        # Experiment exists, update it
        update_query = """
        UPDATE Experiments 
        SET session_id = %s, experiment_name = %s, database_source = %s
        WHERE experiment_id = %s
        """
        params = (session_id, experiment_name, database_source, experiment_id)
        repo_conn.execute(update_query, params)
        print(f"Updated experiment: {experiment_id}")
    else:
        # Create new experiment
        insert_query = """
        INSERT INTO Experiments (experiment_id, session_id, experiment_name, database_source) 
        VALUES (%s, %s, %s, %s)
        """
        params = (experiment_id, session_id, experiment_name, database_source)
        repo_conn.execute(insert_query, params)
        print(f"Created new experiment: {experiment_id}")

    return experiment_id


def read_cluster_info(conn):
    """
    Read cluster info from source database

    Args:
        conn: Source database connection

    Returns:
        List of tuples containing (experiment_id, gen_id, channel)
    """
    conn.execute(
        """
        SELECT c1.experiment_id, c1.gen_id, c1.channel
        FROM ClusterInfo c1
        INNER JOIN (
            SELECT channel, MAX(experiment_id) as max_exp_id
            FROM ClusterInfo
            GROUP BY channel
        ) c2 ON c1.channel = c2.channel AND c1.experiment_id = c2.max_exp_id
        INNER JOIN (
            SELECT channel, experiment_id, MAX(gen_id) as max_gen_id
            FROM ClusterInfo
            GROUP BY channel, experiment_id
        ) c3 ON c1.channel = c3.channel AND c1.experiment_id = c3.experiment_id AND c1.gen_id = c3.max_gen_id
        """
    )

    return conn.fetch_all()


def write_cluster_info_to_db(conn, experiment_id, cluster_info):
    """
    Write cluster info to repository database

    Args:
        conn: Repository database connection
        experiment_id: The experiment ID to use for the export
        cluster_info: List of tuples containing (original_experiment_id, gen_id, channel)
    """
    for cluster in cluster_info:
        orig_experiment_id = cluster[0]
        gen_id = cluster[1]
        channel = cluster[2]

        # Format cluster_id as experiment_id_gen_id from the original data
        cluster_id = f"{orig_experiment_id}_{gen_id}"

        # Insert into repository database using the new experiment_id from the function parameter
        conn.execute(
            """
            INSERT INTO ClusterInfo (experiment_id, cluster_id, channel, gen_id) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                channel = VALUES(channel),
                gen_id = VALUES(gen_id)
            """,
            params=(experiment_id, cluster_id, channel, gen_id)
        )

    print(f"Successfully exported {len(cluster_info)} cluster records")


def read_stim_task_mapping(df):
    """
    Read stimulus and task mapping from the dataframe

    Args:
        df: DataFrame containing TaskId and StimSpecId columns

    Returns:
        Dictionary with unique stim IDs and task-stim pairs
    """
    # Extract unique stim IDs
    unique_stim_ids = df['StimSpecId'].unique().tolist()

    # Create task-stim pairs
    task_stim_pairs = []
    for _, row in df.iterrows():
        task_id = row['TaskId']
        stim_id = row['StimSpecId']
        task_stim_pairs.append((task_id, stim_id))

    return {
        'unique_stim_ids': unique_stim_ids,
        'task_stim_pairs': task_stim_pairs
    }


def write_stim_experiment_mapping(conn, experiment_id, stim_task_mapping):
    """
    Write stimulus-experiment mapping to repository database

    Args:
        conn: Repository database connection
        experiment_id: Experiment ID to associate with stimuli
        stim_task_mapping: Dictionary with unique stim IDs
    """
    unique_stim_ids = stim_task_mapping['unique_stim_ids']

    # Insert each unique stim ID with the experiment ID using ON DUPLICATE KEY UPDATE
    for stim_id in unique_stim_ids:
        conn.execute(
            """
            INSERT INTO StimExperimentMapping (stim_id, experiment_id) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE experiment_id = VALUES(experiment_id)
            """,
            params=(stim_id, experiment_id)
        )

    print(f"Successfully exported {len(unique_stim_ids)} stimulus-experiment mappings")


def write_task_stim_mapping(conn, stim_task_mapping):
    """
    Write task-stimulus mapping to repository database

    Args:
        conn: Repository database connection
        stim_task_mapping: Dictionary with task-stim pairs
    """
    task_stim_pairs = stim_task_mapping['task_stim_pairs']

    # Insert each task-stim pair with ON DUPLICATE KEY UPDATE
    for task_id, stim_id in task_stim_pairs:
        conn.execute(
            """
            INSERT INTO TaskStimMapping (task_id, stim_id) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE stim_id = VALUES(stim_id)
            """,
            params=(task_id, stim_id)
        )

    print(f"Successfully exported {len(task_stim_pairs)} task-stimulus mappings")


def read_raw_spike_responses(df, to_export_conn):
    """
    Read raw spike responses from the dataframe and original database

    Args:
        df: DataFrame containing TaskId information
        to_export_conn: Connection to the source database

    Returns:
        List of tuples containing task-channel-response data
    """
    # Get all task IDs from the dataframe
    task_ids = df['TaskId'].unique().tolist()

    # For each task ID, get spike responses for all channels
    responses = []
    for task_id in task_ids:
        # Query to get spike data for this task
        to_export_conn.execute(
            """
            SELECT channel_id, tstamps, response_rate 
            FROM RawSpikeResponses 
            WHERE task_id = %s
            """,
            params=(task_id,)
        )

        task_responses = to_export_conn.fetch_all()
        for channel_id, tstamps, response_rate in task_responses:
            responses.append((task_id, channel_id, tstamps, response_rate))

    return responses


def write_raw_spike_responses(conn, raw_responses):
    """
    Write raw spike responses to repository database

    Args:
        conn: Repository database connection
        raw_responses: List of tuples containing (task_id, channel_id, tstamps, response_rate)
    """
    for task_id, channel_id, tstamps, response_rate in raw_responses:
        conn.execute(
            """
            INSERT INTO RawSpikeResponses (task_id, channel_id, tstamps, response_rate) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                tstamps = VALUES(tstamps),
                response_rate = VALUES(response_rate)
            """,
            params=(task_id, channel_id, tstamps, response_rate)
        )

    print(f"Successfully exported {len(raw_responses)} raw spike responses")


def read_isogabor_stim_info(to_export_conn, stim_task_mapping):
    """
    Read IsoGabor stimulus info from the source database

    Args:
        to_export_conn: Connection to the source database
        stim_task_mapping: Dictionary with unique stim IDs

    Returns:
        List of IsoGabor stim IDs
    """
    unique_stim_ids = stim_task_mapping['unique_stim_ids']
    isogabor_stim_ids = []

    for stim_id in unique_stim_ids:
        # Check if this stimulus is an IsoGabor stimulus
        to_export_conn.execute(
            """
            SELECT spec FROM StimSpec WHERE id = %s
            """,
            params=(stim_id,)
        )

        result = to_export_conn.fetch_all()
        if result:
            spec = result[0][0]
            if spec and 'IsoGabor' in spec:  # Simple check for IsoGabor stimuli
                isogabor_stim_ids.append(stim_id)

    return isogabor_stim_ids


def write_isogabor_stim_info(conn, isogabor_stim_ids):
    """
    Write IsoGabor stimulus info to repository database

    Args:
        conn: Repository database connection
        isogabor_stim_ids: List of IsoGabor stim IDs
    """
    for stim_id in isogabor_stim_ids:
        conn.execute(
            """
            INSERT INTO IsoGaborStimInfo (stim_id) 
            VALUES (%s)
            ON DUPLICATE KEY UPDATE stim_id = VALUES(stim_id)
            """,
            params=(stim_id,)
        )

    print(f"Successfully exported {len(isogabor_stim_ids)} IsoGabor stimulus records")
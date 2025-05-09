import pandas as pd
import xmltodict
import datetime
from clat.util.connection import Connection
from typing import Tuple, Dict, List, Any, Hashable


def export_to_repository(df: pd.DataFrame, db_name: str, exp_name: str,
                         stim_info_table: str = "None", stim_info_columns: List[str] = None):
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

    # Epochs
    epochs = read_epochs(df)
    write_epochs_to_db(repo_conn, epochs)

    # Raw Spike Responses
    raw_spike_responses = read_raw_spike_responses(df)
    write_raw_spike_responses(repo_conn, raw_spike_responses)

    # IsoGaborStimInfo
    stim_info = read_stim_info(df, stim_info_columns)
    write_stim_info_to_db(repo_conn, stim_info_table, stim_info, stim_task_mapping)
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
            params=(int(stim_id), experiment_id)
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
            params=(int(task_id), int(stim_id))
        )

    print(f"Successfully exported {len(task_stim_pairs)} task-stimulus mappings")


def read_epochs(df: pd.DataFrame) -> Dict[int, Tuple[float, float]]:
    """
    Read epoch data from the DataFrame

    Args:
        df: DataFrame containing TaskId and Epochs By Channel columns

    Returns:
        Dictionary mapping task IDs to (epoch_start, epoch_end) tuples
    """
    epochs_data = {}

    # Check if the DataFrame has the required column
    if 'Epoch' not in df.columns:
        print("Warning: 'Epochs By Channel' column not found in DataFrame")
        return epochs_data

    # Extract epoch data for each task
    for _, row in df.iterrows():
        task_id = row['TaskId']
        epoch = row['Epoch']

        # Skip if no epoch data
        if epoch is None or epoch == "None" or not epoch:
            continue

        # Assume all channels have the same epoch, so take the first one
        # Epochs are typically stored as a dict with channel as key and (start, end) as value

        epochs_data[task_id] = epoch

    print(f"Found epoch data for {len(epochs_data)} tasks")
    return epochs_data


def write_epochs_to_db(conn: Connection, epochs_data: Dict[int, Tuple[float, float]]):
    """
    Write epoch data to the Epochs table

    Args:
        conn: Repository database connection
        epochs_data: Dictionary mapping task IDs to (epoch_start, epoch_end) tuples
    """
    for task_id, (epoch_start, epoch_end) in epochs_data.items():
        query = """
        INSERT INTO Epochs (task_id, epoch_start, epoch_end)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE epoch_start = %s, epoch_end = %s
        """
        params = (int(task_id), float(epoch_start), epoch_end, epoch_start, epoch_end)
        conn.execute(query, params)

    print(f"Successfully exported {len(epochs_data)} epoch records")


def read_raw_spike_responses(df: pd.DataFrame) -> List[Tuple[int, str, str, float]]:
    """
    Read raw spike responses from the DataFrame and calculate accurate spike rates using epoch data.
    Spike timestamps are already relative to epochs, so we just need the epoch duration.

    Args:
        df: DataFrame containing TaskId, Spikes by Channel, and Epochs By Channel columns

    Returns:
        List of tuples containing (task_id, channel_id, tstamps, response_rate)
    """
    responses = []

    # Check if the DataFrame has the required columns
    if 'Spikes by channel' not in df.columns:
        print("Warning: 'Spikes by Channel' column not found in DataFrame")
        raise ValueError("Spikes by Channel column is missing from df. Please ensure the DataFrame contains the 'Spikes by Channel' column with spike data. ")

    if 'Epoch' not in df.columns:
        raise ValueError("Epoch column is missing from df. Please ensure the DataFrame contains the 'Epoch' column with epoch data. ")

    # Extract spike data for each task
    for _, row in df.iterrows():
        task_id = row['TaskId']
        spikes_by_channel = row.get('Spikes by channel')
        epochs_by_channel = row.get('Epoch')

        # Skip if no spike data
        if not spikes_by_channel or spikes_by_channel == "None":
            continue

        # Process each channel's spike data
        for channel, spike_times in spikes_by_channel.items():
            # Skip if no spikes for this channel
            if not spike_times:
                continue

            # Convert spike times list to a string that can be easily converted back to a list
            # Using repr() ensures the output can be parsed by ast.literal_eval()
            tstamps_str = repr(spike_times)

            # Calculate response rate (spikes per second) using epoch duration
            if epochs_by_channel and channel in epochs_by_channel:
                epoch_start, epoch_end = epochs_by_channel[channel]
                slide_length = epoch_end - epoch_start

                # Count spikes between 0 and slide_length
                spikes_in_window = [t for t in spike_times if 0 <= t <= slide_length]

                # Calculate rate (spikes per second)
                response_rate = len(spikes_in_window) / slide_length if slide_length > 0 else 0
            else:
                # Fallback: use simple count if no epoch data (less accurate)
                response_rate = len(spike_times)

            responses.append((task_id, channel, tstamps_str, response_rate))

    print(f"Found spike response data for {len(responses)} task-channel pairs")
    return responses


def write_raw_spike_responses(conn: Connection, raw_responses: List[Tuple[int, str, str, float]]):
    """
    Write raw spike responses to repository database

    Args:
        conn: Repository database connection
        raw_responses: List of tuples containing (task_id, channel_id, tstamps, response_rate)
    """
    success_count = 0

    for task_id, channel_id, tstamps, response_rate in raw_responses:
        try:
            query = """
            INSERT INTO RawSpikeResponses (task_id, channel_id, tstamps, response_rate) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                tstamps = VALUES(tstamps),
                response_rate = VALUES(response_rate)
            """
            params = (int(task_id), channel_id, tstamps, float(response_rate))
            conn.execute(query, params)
            success_count += 1
        except Exception as e:
            print(f"Error storing response for task {task_id}, channel {channel_id}: {e}")

    print(f"Successfully exported {success_count} of {len(raw_responses)} raw spike responses")


def read_stim_info(df: pd.DataFrame, stim_info_columns: List[str]) -> dict[Hashable, dict[str, Any]]:
    """
    Read StimInfo data from the DataFrame

    Args:
        df: DataFrame containing stimulus data
        stim_info_columns: List of column names to extract

    Returns:
        Dictionary mapping stim_ids to dictionaries of column_name->value pairs
    """
    stim_info_data = {}

    # Verify all columns exist
    missing_columns = [col for col in stim_info_columns if col not in df.columns]
    if missing_columns:
        print(f"Warning: The following StimInfo columns were not found in the DataFrame: {missing_columns}")
        stim_info_columns = [col for col in stim_info_columns if col in df.columns]

    if not stim_info_columns:
        print("No valid StimInfo columns found. Skipping StimInfo export.")
        return stim_info_data

    # Ensure 'StimSpecId' is in the dataframe
    if 'StimSpecId' not in df.columns:
        print("Error: 'StimSpecId' column not found in DataFrame. Cannot export StimInfo.")
        return stim_info_data

    # Group by StimSpecId and extract the specified columns
    for stim_id, group in df.groupby('StimSpecId'):
        # Get the first row for each stim_id
        row = group.iloc[0]

        # Extract the specified columns
        stim_data = {}
        for col in stim_info_columns:
            if col in row:
                stim_data[col] = row[col]

        stim_info_data[stim_id] = stim_data

    print(f"Found StimInfo data for {len(stim_info_data)} unique stimuli")
    return stim_info_data


def write_stim_info_to_db(conn: Connection, table_name: str, stim_info_data: Dict[int, Dict[str, Any]],
                          stim_task_mapping: Dict):
    """
    Write StimInfo data to the specified repository table

    Args:
        conn: Repository database connection
        table_name: Name of the StimInfo table to write to
        stim_info_data: Dictionary mapping stim_ids to dictionaries of column_name->value pairs
        stim_task_mapping: Dictionary with unique_stim_ids list for checking against StimExperimentMapping
    """
    import time

    # Create a mapping of original column names to SQL-safe column names
    column_name_mapping = {}

    # Replace spaces with underscores in column names and create mapping
    clean_stim_info_data = {}
    for stim_id, stim_data in stim_info_data.items():
        clean_data = {}
        for col, value in stim_data.items():
            clean_col = col.replace(' ', '_')
            clean_data[clean_col] = value
            column_name_mapping[col] = clean_col
        clean_stim_info_data[stim_id] = clean_data

    stim_info_data = clean_stim_info_data

    # Get the list of unique stim IDs that are already in StimExperimentMapping
    valid_stim_ids = set(stim_task_mapping['unique_stim_ids'])

    # Check if the table exists
    conn.execute(f"SHOW TABLES LIKE '{table_name}'")
    if not conn.fetch_all():
        print(f"Table '{table_name}' does not exist in the repository database. Creating it...")
        # Create the table if it doesn't exist
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
            stim_id BIGINT PRIMARY KEY,
            FOREIGN KEY (stim_id) REFERENCES StimExperimentMapping(stim_id) ON DELETE CASCADE
        );
        """
        conn.execute(create_table_query)
        print(f"Table '{table_name}' created successfully")

        # Wait a moment to ensure the table is fully created
        time.sleep(1)

    # Determine column data types by examining the actual data
    column_types = detect_column_types(stim_info_data)

    # Create a new table with dynamic columns if it doesn't have the required columns
    required_cols = set(col for stim_data in stim_info_data.values() for col in stim_data.keys())

    # Get current table columns and verify stim_id is in the table
    def get_current_columns():
        conn.execute(f"DESCRIBE {table_name}")
        current_cols = [row[0] for row in conn.fetch_all()]
        return current_cols

    current_cols = get_current_columns()

    if 'stim_id' not in current_cols:
        print(f"Error: Table '{table_name}' does not have a 'stim_id' column.")
        raise ValueError(f"Table '{table_name}' must have a 'stim_id' column.")

    # Determine which columns need to be added
    missing_cols = required_cols - set(current_cols)

    # Add columns one by one, verifying each addition before proceeding
    if missing_cols:
        print(f"Adding {len(missing_cols)} missing columns to {table_name}...")

        for col in missing_cols:
            try:
                # Use the detected data type, or VARCHAR as fallback
                sql_type = column_types.get(col, 'VARCHAR(255)')
                print(f"Adding column '{col}' with type '{sql_type}'...")

                # Add the column
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {sql_type}")

                # Verify the column was added with retries
                max_retries = 5
                column_added = False

                for attempt in range(max_retries):
                    # Wait a moment to allow the database to complete the operation
                    time.sleep(0.5)

                    # Check if the column exists now
                    updated_cols = get_current_columns()
                    if col in updated_cols:
                        column_added = True
                        print(f"Successfully added column '{col}'")
                        break
                    else:
                        print(f"Waiting for column '{col}' to appear (attempt {attempt + 1}/{max_retries})...")

                if not column_added:
                    print(f"Warning: Could not verify column '{col}' was added after {max_retries} attempts")
                    # Remove from required columns if we couldn't verify it was added
                    required_cols.discard(col)

            except Exception as e:
                print(f"Error adding column '{col}' to table '{table_name}': {e}")
                # Remove from required columns if we couldn't add it
                required_cols.discard(col)

    # Final check of table columns before inserting data
    current_cols = get_current_columns()
    print(f"Current columns in {table_name}: {', '.join(current_cols)}")

    # Prepare counter for successful exports
    success_count = 0

    # Insert data for each stim_id
    for stim_id, stim_data in stim_info_data.items():
        # Skip if this stim_id is not in StimExperimentMapping
        if stim_id not in valid_stim_ids:
            print(f"Skipping stim_id {stim_id} - not found in StimExperimentMapping")
            continue

        # Only include columns that exist in the table
        valid_cols = ['stim_id'] + [col for col in stim_data.keys() if col in current_cols]

        # Force all values to basic Python types
        valid_data = [int(stim_id)]  # Force stim_id to int
        for col in valid_cols[1:]:
            value = stim_data[col]
            # Force conversion to basic Python types
            if hasattr(value, 'item'):  # This handles numpy types
                try:
                    value = value.item()  # Convert numpy scalar to Python scalar
                except (ValueError, AttributeError):
                    pass

            if isinstance(value, float):  # convert float64 to float otherwise SQL will fail
                value = float(value)
            elif isinstance(value, int):
                value = int(value)
            elif isinstance(value, bool):
                value = bool(value)
            elif isinstance(value, str):
                value = str(value)
            elif value is None:
                value = None
            else:
                # For more complex types, convert to string
                value = str(value)

            valid_data.append(value)

        # Skip if we have no valid columns other than stim_id
        if len(valid_cols) <= 1:
            print(f"Skipping stim_id {stim_id} - no valid columns to insert")
            continue

        # Prepare placeholders for SQL query
        placeholders = ', '.join(['%s'] * len(valid_cols))
        cols_str = ', '.join(valid_cols)
        update_str = ', '.join([f"{col} = VALUES({col})" for col in valid_cols[1:]])

        # Construct and execute the query
        try:
            query = f"""
            INSERT INTO {table_name} ({cols_str}) 
            VALUES ({placeholders})
            """
            # Add ON DUPLICATE KEY UPDATE clause if there are columns to update
            if update_str:
                query += f" ON DUPLICATE KEY UPDATE {update_str}"

            conn.execute(query, tuple(valid_data))
            success_count += 1
        except Exception as e:
            print(f"Error storing StimInfo for stim_id {stim_id}: {e}")
            print(f"Values: {valid_data}")
            print(f"Types: {[type(v).__name__ for v in valid_data]}")

    print(f"Successfully exported {success_count} records to {table_name}")

def detect_column_types(stim_info_data: Dict[int, Dict[str, Any]]) -> Dict[str, str]:
    """
    Detect appropriate SQL data types based on the actual data values.
    Limited to basic types: VARCHAR, INT, BIGINT, FLOAT, and LONGTEXT.

    Args:
        stim_info_data: Dictionary mapping stim_ids to dictionaries of column_name->value pairs

    Returns:
        Dictionary mapping column names to SQL data types
    """
    import numpy as np

    # Initialize dictionary to track the type of each column
    column_types = {}
    column_values = {}

    # Collect all values for each column
    for stim_data in stim_info_data.values():
        for col, value in stim_data.items():
            if col not in column_values:
                column_values[col] = []
            if value is not None:  # Skip None values for type detection
                column_values[col].append(value)

    # Analyze each column's values to determine the appropriate type
    for col, values in column_values.items():
        if not values:  # If no values (all None), default to VARCHAR
            column_types[col] = 'VARCHAR(255)'
            continue

        # Sample some values (up to 100) to detect type
        sample_values = values[:100]

        # Check if all values are integers
        if all(isinstance(v, (int, np.int64, np.int32)) for v in sample_values):
            # Determine if it's a regular INT or BIGINT
            max_val = max(sample_values)
            min_val = min(sample_values)

            if min_val >= -2147483648 and max_val <= 2147483647:
                column_types[col] = 'INT'
            else:
                column_types[col] = 'BIGINT'

        # Check if all values are floating point numbers
        elif all(isinstance(v, (float, np.float64, np.float32)) for v in sample_values):
            column_types[col] = 'FLOAT'

        # For text content, consider length
        elif all(isinstance(v, str) for v in sample_values):
            max_length = max(len(str(v)) for v in sample_values)

            # Use VARCHAR for shorter strings
            if max_length <= 200:
                column_types[col] = 'VARCHAR(255)'
            # Use LONGTEXT for very long strings
            elif max_length > 1000:
                column_types[col] = 'LONGTEXT'
            # Use medium VARCHAR for in-between
            else:
                column_types[col] = 'VARCHAR(1000)'

        # Everything else is VARCHAR
        else:
            column_types[col] = 'VARCHAR(255)'

    return column_types

import pandas as pd
import ast
from typing import Dict, List, Any, Tuple, Optional
from clat.util.connection import Connection


def import_from_repository(session_id: str, experiment_name: str,
                           stim_info_table: str, response_table: str) -> pd.DataFrame:
    """
    Import data from the repository database based on session_id and experiment_name.

    Args:
        session_id: Session ID string (e.g., "250427_0")
        experiment_name: Name of the experiment (e.g., "Isogabor")
        stim_info_table: Name of the stimulus info table to query (e.g., "IsoGaborStimInfo")
        response_table: Name of the response table to query (e.g., "RawSpikeResponses" or "WindowSortedResponses")

    Returns:
        DataFrame containing combined data from repository
    """
    # Connect to repository database
    repo_conn = Connection("allen_data_repository")

    # Form the experiment_id from session_id and experiment_name
    experiment_id = f"{session_id}_{experiment_name}"

    print(f"Importing data for experiment: {experiment_id}")

    # Check if experiment exists
    repo_conn.execute(
        "SELECT experiment_id FROM Experiments WHERE experiment_id = %s",
        params=(experiment_id,)
    )
    result = repo_conn.fetch_all()

    if not result:
        raise ValueError(f"Experiment '{experiment_id}' not found in repository")

    # 1. Get all stim_ids for this experiment from StimExperimentMapping
    repo_conn.execute(
        "SELECT stim_id FROM StimExperimentMapping WHERE experiment_id = %s",
        params=(experiment_id,)
    )
    stim_ids = [row[0] for row in repo_conn.fetch_all()]

    if not stim_ids:
        raise ValueError(f"No stimuli found for experiment '{experiment_id}'")

    print(f"Found {len(stim_ids)} stimuli for this experiment")

    # 2. Get task_ids from TaskStimMapping for these stim_ids
    placeholders = ', '.join(['%s'] * len(stim_ids))
    repo_conn.execute(
        f"SELECT task_id, stim_id FROM TaskStimMapping WHERE stim_id IN ({placeholders})",
        params=stim_ids
    )
    task_stim_pairs = [(row[0], row[1]) for row in repo_conn.fetch_all()]

    task_ids = [pair[0] for pair in task_stim_pairs]

    if not task_ids:
        raise ValueError(f"No tasks found for stimuli in experiment '{experiment_id}'")

    print(f"Found {len(task_ids)} tasks for this experiment")

    # 3. Get stim info from specified table
    # First, get the column names from the specified table
    repo_conn.execute(f"DESCRIBE {stim_info_table}")
    stim_info_columns = [row[0] for row in repo_conn.fetch_all()]

    # Remove 'stim_id' from columns list as we'll handle it separately
    if 'stim_id' in stim_info_columns:
        stim_info_columns.remove('stim_id')

    # If no columns available
    if not stim_info_columns:
        print(f"Warning: No additional columns found in {stim_info_table}")
        stim_info_data = {}
    else:
        columns_str = ', '.join(['stim_id'] + stim_info_columns)
        placeholders = ', '.join(['%s'] * len(stim_ids))

        repo_conn.execute(
            f"SELECT {columns_str} FROM {stim_info_table} WHERE stim_id IN ({placeholders})",
            params=stim_ids
        )

        stim_info_data = {}
        for row in repo_conn.fetch_all():
            stim_id = row[0]
            values = row[1:]
            stim_info_data[stim_id] = dict(zip(stim_info_columns, values))

    print(f"Retrieved stimulus information from {stim_info_table}")

    # 4. Get response data - first identify the structure of the response table
    repo_conn.execute(f"DESCRIBE {response_table}")
    response_columns = [row[0] for row in repo_conn.fetch_all()]

    # Identify primary keys (excluding task_id)
    primary_keys = [col for col in response_columns
                    if col.endswith('_id') and col != 'task_id']

    if not primary_keys:
        raise ValueError(f"No suitable ID column found in {response_table}")

    # Use the first ID column found
    id_column = primary_keys[0]
    print(f"Using {id_column} as the ID column for responses")

    # Get response data
    placeholders = ', '.join(['%s'] * len(task_ids))
    repo_conn.execute(
        f"SELECT task_id, {id_column}, tstamps, response_rate FROM {response_table} "
        f"WHERE task_id IN ({placeholders})",
        params=task_ids
    )

    # Process response data
    responses_data = {}
    for row in repo_conn.fetch_all():
        task_id = row[0]
        id_value = row[1]
        tstamps_str = row[2]
        response_rate = row[3]

        # Initialize nested dictionaries if needed
        if task_id not in responses_data:
            responses_data[task_id] = {
                'tstamps': {},
                'response_rate': {}
            }

        # Convert timestamp string back to list using ast.literal_eval
        try:
            tstamps_list = ast.literal_eval(tstamps_str)
        except (SyntaxError, ValueError):
            print(f"Warning: Could not parse timestamps for task {task_id}, {id_column} {id_value}")
            tstamps_list = []

        responses_data[task_id]['tstamps'][id_value] = tstamps_list
        responses_data[task_id]['response_rate'][id_value] = response_rate

    print(f"Retrieved response data from {response_table}")

    # 5. Get epochs data for all tasks
    placeholders = ', '.join(['%s'] * len(task_ids))
    repo_conn.execute(
        f"SELECT task_id, epoch_start, epoch_end FROM Epochs WHERE task_id IN ({placeholders})",
        params=task_ids
    )

    epochs_data = {}
    for row in repo_conn.fetch_all():
        task_id = row[0]
        epoch_start = row[1]
        epoch_end = row[2]
        epochs_data[task_id] = (epoch_start, epoch_end)

    print(f"Retrieved epoch data for {len(epochs_data)} tasks")

    # 6. Compile all data into a DataFrame
    compiled_data = []
    for task_id, stim_id in task_stim_pairs:
        # Create base row with task and stim IDs
        row_data = {
            'TaskId': task_id,
            'StimSpecId': stim_id
        }

        # Add stim info data if available
        if stim_id in stim_info_data:
            for col_name, value in stim_info_data[stim_id].items():
                row_data[col_name] = value

        # Add response data if available
        if task_id in responses_data:
            # Store as dictionaries to match your existing format
            row_data[f'Spikes by {id_column.replace("_id", "")}'] = responses_data[task_id]['tstamps']
            row_data[f'Response Rate by {id_column.replace("_id", "")}'] = responses_data[task_id]['response_rate']

        # Add epoch data if available
        if task_id in epochs_data:
            row_data['Epoch'] = epochs_data[task_id]

        compiled_data.append(row_data)

    # Create DataFrame and return
    df = pd.DataFrame(compiled_data)
    print(f"Successfully compiled data into DataFrame with {len(df)} rows and {len(df.columns)} columns")

    return df

if __name__ == "__main__":


    df = import_from_repository("250427_0",
                                "isogabor",
                                "IsoGaborStimInfo",
                                "RawSpikeResponses")
    print(df.to_string())
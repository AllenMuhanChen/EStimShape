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
    experiment_id, stim_ids = fetch_experiment_id_and_stims_for_session(session_id, experiment_name=experiment_name, repo_conn=repo_conn)

    # 2. Get task_ids from TaskStimMapping for these stim_ids
    task_ids, task_stim_pairs = fetch_task_ids_and_task_stim_mappings(experiment_id, repo_conn, stim_ids)

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
    statement = f"SELECT task_id, {id_column}, tstamps, response_rate FROM {response_table} " \
                    f"WHERE task_id IN ({placeholders})"
    repo_conn.execute(
        statement,
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

    # 6. Compile all data into a DataFrame
    compiled_data = []
    for task_id, stim_id in task_stim_pairs:

        if stim_id not in stim_info_data or task_id not in responses_data:
            continue

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


        compiled_data.append(row_data)

    # Create DataFrame and return
    df = pd.DataFrame(compiled_data)
    print(f"Successfully compiled data into DataFrame with {len(df)} rows and {len(df.columns)} columns")

    return df


def fetch_task_ids_and_task_stim_mappings(experiment_id, repo_conn, stim_ids):
    """
    Fetch task IDs and task-stim mappings for the given stim IDs.

    Args:
        experiment_id: Single experiment ID string or list of experiment ID strings
        repo_conn: Database connection to repository
        stim_ids: List of stimulus IDs or dictionary mapping experiment IDs to stimulus ID lists

    Returns:
        Tuple of (task_ids, task_stim_pairs)
    """
    # Handle different input types
    if isinstance(experiment_id, list):
        # Multiple experiments case
        all_task_ids = []
        all_task_stim_pairs = []

        # If stim_ids is a dictionary mapping experiment IDs to stim lists
        if isinstance(stim_ids, dict):
            for exp_id in experiment_id:
                exp_stim_ids = stim_ids.get(exp_id, [])
                if not exp_stim_ids:
                    print(f"Warning: No stimulus IDs found for experiment '{exp_id}'")
                    continue

                # Process this experiment's stimuli
                task_ids, task_stim_pairs = _fetch_task_stim_mappings_for_stims(exp_id, repo_conn, exp_stim_ids)
                all_task_ids.extend(task_ids)
                all_task_stim_pairs.extend(task_stim_pairs)
        else:
            # If stim_ids is a flat list, use same stim_ids for all experiments
            task_ids, task_stim_pairs = _fetch_task_stim_mappings_for_stims(experiment_id, repo_conn, stim_ids)
            all_task_ids.extend(task_ids)
            all_task_stim_pairs.extend(task_stim_pairs)

        # Check if we found any tasks
        if not all_task_ids:
            raise ValueError(f"No tasks found for stimuli in experiments: {experiment_id}")

        print(f"Found {len(all_task_ids)} tasks across {len(experiment_id)} experiments")
        return all_task_ids, all_task_stim_pairs
    else:
        # Single experiment case - use the original logic
        return _fetch_task_stim_mappings_for_stims(experiment_id, repo_conn, stim_ids)


def _fetch_task_stim_mappings_for_stims(experiment_id, repo_conn, stim_ids):
    """Helper function to fetch task-stim mappings for a list of stimulus IDs"""
    if not stim_ids:
        return [], []

    placeholders = ', '.join(['%s'] * len(stim_ids))
    repo_conn.execute(
        f"SELECT task_id, stim_id FROM TaskStimMapping WHERE stim_id IN ({placeholders})",
        params=stim_ids
    )
    task_stim_pairs = [(row[0], row[1]) for row in repo_conn.fetch_all()]
    task_ids = [pair[0] for pair in task_stim_pairs]

    if not task_ids:
        print(f"Warning: No tasks found for stimuli in experiment '{experiment_id}'")
        return [], []

    print(f"Found {len(task_ids)} tasks for experiment '{experiment_id}'")
    return task_ids, task_stim_pairs


def fetch_experiment_id_and_stims_for_session(session_id, experiment_name=None, repo_conn=None):
    """
    Fetch experiment IDs and their associated stimuli for a given session.

    Args:
        session_id (str): The session ID to query
        experiment_name (str, optional): If provided, returns data only for this specific experiment
        repo_conn: Database connection to repository

    Returns:
        If experiment_name is provided:
            Tuple of (experiment_id, stim_ids)
        If experiment_name is None:
            Tuple of (list_of_experiment_ids, dict_mapping_experiment_id_to_stim_ids)
    """
    if experiment_name:
        # Original functionality - single experiment
        experiment_id = f"{session_id}_{experiment_name}"
        check_experiment_id_valid(experiment_id, repo_conn)
        stim_ids = fetch_stim_ids_for_experiment_id(experiment_id, repo_conn)
        return experiment_id, stim_ids
    else:
        # Get all experiments for this session
        repo_conn.execute(
            "SELECT experiment_id FROM Experiments WHERE session_id = %s",
            params=(session_id,)
        )
        experiment_ids = [row[0] for row in repo_conn.fetch_all()]

        if not experiment_ids:
            raise ValueError(f"No experiments found for session '{session_id}'")

        print(f"Found {len(experiment_ids)} experiments for session {session_id}")

        # Get stim IDs for each experiment
        experiment_to_stims = {}
        for exp_id in experiment_ids:
            stim_ids = fetch_stim_ids_for_experiment_id(exp_id, repo_conn)
            experiment_to_stims[exp_id] = stim_ids

        return experiment_ids, experiment_to_stims

def fetch_stim_ids_for_experiment_id(experiment_id, repo_conn):
    repo_conn.execute(
        "SELECT stim_id FROM StimExperimentMapping WHERE experiment_id = %s",
        params=(experiment_id,)
    )
    stim_ids = [row[0] for row in repo_conn.fetch_all()]
    if not stim_ids:
        raise ValueError(f"No stimuli found for experiment '{experiment_id}'")
    print(f"Found {len(stim_ids)} stimuli for this experiment")
    return stim_ids


def check_experiment_id_valid(experiment_id, repo_conn):
    print(f"Importing data for experiment: {experiment_id}")
    # Check if experiment exists
    repo_conn.execute(
        "SELECT experiment_id FROM Experiments WHERE experiment_id = %s",
        params=(experiment_id,)
    )
    result = repo_conn.fetch_all()
    if not result:
        raise ValueError(f"Experiment '{experiment_id}' not found in repository")


if __name__ == "__main__":


    df = import_from_repository("250427_0",
                                "isogabor",
                                "IsoGaborStimInfo",
                                "RawSpikeResponses")
    print(df.to_string())
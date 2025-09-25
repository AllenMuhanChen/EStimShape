from typing import Optional

from clat.intan.one_file_spike_parsing import OneFileParser
from clat.intan.rhs import load_intan_rhs_format

from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.analysis.isogabor.old_isogabor_analysis import read_pickle
from src.intan.MultiFileParser import MultiFileParser

from src.repository.import_from_repository import fetch_experiment_id_and_stims_for_session, \
    fetch_task_ids_and_task_stim_mappings


def main():
    session_id = "250506_0"
    label = None
    export_sorted_spikes(session_id, label=label)


def export_sorted_spikes(session_id, label: Optional[str] = None):
    """
    Export sorted spikes to the Allen Data Repository.
    :param session_id: The session ID to export.
    :param label: Optional label to append to the sorted spikes file name. If
    reading from a labelled spike sorting, then this label will be added to unit names
    """
    repo_conn = Connection("allen_data_repository")
    sort_dir = "/home/connorlab/Documents/EStimShape/allen_sort_%s" % session_id
    if label:
        sorted_spikes_path = f"{sort_dir}/sorted_spikes_{label}.pkl"
    else:
        sorted_spikes_path = f"{sort_dir}/sorted_spikes.pkl"
    rhs_data = load_intan_rhs_format.read_data(f"{sort_dir}/info.rhs")
    sample_rate = rhs_data['frequency_parameters']['amplifier_sample_rate']
    experiment_id, stim_ids = fetch_experiment_id_and_stims_for_session(session_id,
                                                                        repo_conn=repo_conn)

    parser = OneFileParser()
    task_ids, task_stim_pairs = fetch_task_ids_and_task_stim_mappings(experiment_id, repo_conn, stim_ids)
    epochs_for_task_ids = parser.parse_epochs(sort_dir, sample_rate)
    for task_id, epoch in epochs_for_task_ids.items():
        print(f"Epoch for {task_id} is {epoch}")
    # epochs_for_task_ids = fetch_epochs_for_task_ids(task_ids, repo_conn)
    spike_indices_by_unit_by_channel = read_pickle(sorted_spikes_path)
    spike_tstamps_by_task_id_by_unit = {}
    spike_rates_by_task_id_by_unit = {}
    for task_id in task_ids:
        if task_id not in epochs_for_task_ids:
            print(f"Skipping task_id {task_id} because it is not in epochs_for_task_ids")
            continue
        spike_tstamps_by_task_id_by_unit[task_id] = {}
        spike_rates_by_task_id_by_unit[task_id] = {}
        epochs = epochs_for_task_ids[task_id]
        if epochs is None:
            print(f"Skipping task_id {task_id} because epochs are None")
            continue
        task_duration = epochs[1] - epochs[0]
        for channel, spike_indices_by_unit in spike_indices_by_unit_by_channel.items():
            for unit_name, spike_indices in spike_indices_by_unit.items():
                if label:
                    new_unit_name = f"{label}_{channel.value}_{unit_name}"
                else:
                    new_unit_name = f"{channel.value}_{unit_name}"
                if new_unit_name not in spike_tstamps_by_task_id_by_unit[task_id]:
                    spike_tstamps_by_task_id_by_unit[task_id][new_unit_name] = []

                start_index = (epochs[0] - 0.2) * sample_rate
                stop_index = (epochs[1] + 0.2) * sample_rate
                qualifying_spikes = [spike_index for spike_index in spike_indices if
                                     start_index <= spike_index <= stop_index]
                # Make tstamps relative to epoch
                spikes_relative_tstamps = [(spike_index / sample_rate) - epochs[0] for spike_index in qualifying_spikes]
                spike_tstamps_by_task_id_by_unit[task_id][new_unit_name].extend(spikes_relative_tstamps)
                # Calculate spike rate
                within_epoch_spikes = [spike_relative_tstamp for spike_relative_tstamp in spikes_relative_tstamps if
                                       0 <= spike_relative_tstamp <= task_duration]
                spike_rate = len(within_epoch_spikes) / task_duration
                spike_rates_by_task_id_by_unit[task_id][new_unit_name] = spike_rate
    print(f"Found {len(spike_tstamps_by_task_id_by_unit)} task IDs with spikes")
    write_sorted_spikes_to_repository(spike_tstamps_by_task_id_by_unit, spike_rates_by_task_id_by_unit, repo_conn)


def write_sorted_spikes_to_repository(spike_tstamps_by_task_id_by_unit,
                                      spike_rates_by_task_id_by_unit,
                                      repo_conn):
    """
    Write sorted spike timestamps and rates to the WindowSortedResponses table in the repository.

    Args:
        spike_tstamps_by_task_id_by_unit: Dictionary mapping task IDs to dictionaries of unit names and spike timestamps
        spike_rates_by_task_id_by_unit: Dictionary mapping task IDs to dictionaries of unit names and spike rates
        repo_conn: Connection object to the repository database
    """
    success_count = 0
    total_count = 0

    for task_id, unit_spike_tstamps in spike_tstamps_by_task_id_by_unit.items():
        for unit_id, spike_tstamps in unit_spike_tstamps.items():
            total_count += 1

            # Get spike rate if available, otherwise default to 0
            spike_rate = 0
            if task_id in spike_rates_by_task_id_by_unit and unit_id in spike_rates_by_task_id_by_unit[task_id]:
                spike_rate = spike_rates_by_task_id_by_unit[task_id][unit_id]

            # Convert spike timestamps list to string representation
            tstamps_str = repr(spike_tstamps)

            try:
                # Insert or update the WindowSortedResponses table
                query = """
                INSERT INTO WindowSortedResponses (task_id, unit_id, tstamps, response_rate) 
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    tstamps = VALUES(tstamps),
                    response_rate = VALUES(response_rate)
                """
                params = (int(task_id), unit_id, tstamps_str, float(spike_rate))
                repo_conn.execute(query, params)
                success_count += 1

                if success_count % 100 == 0:
                    print(f"Exported {success_count} of {total_count} responses so far...")

            except Exception as e:
                print(f"Error storing response for task {task_id}, unit {unit_id}: {e}")

    print(f"Successfully exported {success_count} of {total_count} window sorted responses")

def fetch_epochs_for_task_ids(task_ids, repo_conn):
    """
    Fetch epoch data for a list of task IDs from the repository database.

    Args:
        task_ids: List of task IDs to fetch epochs for
        repo_conn: Connection object to the repository database

    Returns:
        Dictionary mapping task IDs to epoch tuples (start, end)
    """
    # Create placeholders for the SQL query
    placeholders = ', '.join(['%s'] * len(task_ids))

    # Execute the query to fetch epochs for all task IDs
    repo_conn.execute(
        f"SELECT task_id, epoch_start, epoch_end FROM Epochs WHERE task_id IN ({placeholders})",
        params=task_ids
    )

    # Process results into a dictionary
    epochs_data = {}
    for row in repo_conn.fetch_all():
        task_id = row[0]
        epoch_start = row[1]
        epoch_end = row[2]
        epochs_data[task_id] = (epoch_start, epoch_end)

    print(f"Retrieved epoch data for {len(epochs_data)} of {len(task_ids)} tasks")

    # Fill in missing epochs with None if needed
    for task_id in task_ids:
        if task_id not in epochs_data:
            epochs_data[task_id] = None
            print(f"Warning: No epoch data found for task_id {task_id}")

    return epochs_data


if __name__ == "__main__":
    main()

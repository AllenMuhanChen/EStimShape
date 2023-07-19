import os

from intan.livenotes import map_stim_id_to_tstamps
from intan.marker_channels import get_epochs_start_and_stop_indices
from intan.spike_file import read_intan_spike_file, read_digitalin_file, spike_matrix_to_spike_tstamps_for_channels


def fetch_spike_tstamps_from_file(spike_file_path):
    spike_matrix, sample_rate = read_intan_spike_file(spike_file_path)
    spike_tstamps_for_channels = spike_matrix_to_spike_tstamps_for_channels(spike_matrix)
    return spike_tstamps_for_channels


def filter_spikes_with_stim_tstamps(spike_tstamps_for_channels, tstamps_for_stim_ids, stim_id):
    passed_filter = []
    tstamps = tstamps_for_stim_ids[stim_id]
    for channel in spike_tstamps_for_channels:
        for spike_tstamp in channel:
            if spike_tstamp >= tstamps[0] or spike_tstamp <= tstamps[1]:
                passed_filter.append(spike_tstamp)
    return passed_filter


class ResponseParser:
    def __init__(self, base_intan_path: str):
        self.intan_spike_path = base_intan_path

    def parse_avg_spike_count_for_stim(self, stim_id):
        # Find the taks_ids for a stim_id

        # Parse all the spike counts
        # Add each to response_vector

        # average the spike counts
        # Assign as response
        pass

    def parse_spike_count_for_task(self, task_id):
        spike_tstamps_for_channels, sample_rate = fetch_spike_tstamps_from_file(self.path_to_spike(task_id))
        digital_in = read_digitalin_file(self.path_to_digital_in(task_id))
        stim_tstamps_from_markers = get_epochs_start_and_stop_indices(digital_in[0], digital_in[1])
        stim_id_for_tstamps = map_stim_id_to_tstamps(self.path_to_notes(task_id), stim_tstamps_from_markers)
        spikes_for_channels = filter_spikes_with_stim_tstamps(spike_tstamps_for_channels, stim_id_for_tstamps, task_id)
        return len(spikes_for_channels)

    def path_to_trial(self, task_id):
        paths_to_trial = find_folders_with_id(self.intan_spike_path, task_id)
        if len(paths_to_trial) == 1:
            return paths_to_trial[0]
        else:
            # find the most recent one based on timestamps on files
            date_times = [date_time_for_folder(path) for path in paths_to_trial]
            return paths_to_trial[date_times.index(max(date_times))]

    def path_to_spike(self, stim_id: int) -> str:
        path_to_trial = self.path_to_trial(stim_id)
        pass

    def path_to_digital_in(self, stim_id: int) -> str:
        pass

    def path_to_notes(self, stim_id: int) -> str:
        pass


def find_folders_with_id(root_directory, id: int):
    matching_directories = []

    # List all directories under the root directory
    for dirpath, dirnames, filenames in os.walk(root_directory):
        for dirname in dirnames:
            # Split the directory name into ids and date_time
            ids, date_time = dirname.split('__')

            # Check if the specified id is in the list of ids
            if str(id) in ids.split('_'):
                # If it is, add the full directory path to the list
                matching_directories.append(os.path.join(dirpath, dirname))

    return matching_directories


def date_time_for_folder(folder_path: str) -> int:
    # Split the directory name into ids and date_time
    ids, date_time = os.path.basename(folder_path).split('__')

    return int(date_time.replace('_', ''))


def count_spikes_for_channels(spike_tstamps_for_channels):
    spike_counts_for_channels = {}
    for channel_name, spike_tstamps in spike_tstamps_for_channels.items():
        spike_counts_for_channels[channel_name] = len(spike_tstamps)
    return spike_counts_for_channels

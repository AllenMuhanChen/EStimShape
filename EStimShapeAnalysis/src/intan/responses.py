import os
from datetime import datetime
from typing import Dict, List

from intan.channels import Channel
from intan.livenotes import map_stim_id_to_epochs_with_livenotes
from intan.marker_channels import epoch_using_marker_channels
from intan.spike_file import fetch_spike_tstamps_from_file


class ResponseParser:
    def __init__(self, base_intan_path: str, channels: list[Channel] = None, date: str = None):
        if date is None:
            self.date = get_current_date()
        else:
            self.date = date
        self.intan_spike_path = base_intan_path
        self.intan_spike_path = os.path.join(self.intan_spike_path, self.date)
        self.channels = channels


    def parse_avg_spike_count_for_stim(self, stim_id):
        pass
        # Find the taks_ids for a stim_id

        # Parse all the spike counts
        # Add each to response_vector

        # average the spike counts
        # Assign as response

    def parse_spike_count_for_task(self, task_id):
        spike_tstamps_for_channels = fetch_spike_tstamps_from_file(self.path_to_spike_file(task_id))
        stim_epochs_from_markers = epoch_using_marker_channels(self.path_to_digital_in(task_id))
        stim_id_for_epochs = map_stim_id_to_epochs_with_livenotes(self.path_to_notes(task_id),
                                                                  stim_epochs_from_markers)
        spikes_for_channels = filter_spikes_with_epochs(spike_tstamps_for_channels, stim_id_for_epochs, task_id)
        # Count spikes for each channel
        total_spike_count = 0
        for channel in self.channels:
            total_spike_count += len(spikes_for_channels[channel])
        return total_spike_count

    def path_to_trial(self, task_id) -> str:
        paths_to_trial = find_folders_with_id(self.intan_spike_path, task_id)
        if len(paths_to_trial) == 1:
            return paths_to_trial[0]
        elif len(paths_to_trial) > 1:
            # find the most recent one based on timestamps on files
            date_times = [date_time_for_folder(path) for path in paths_to_trial]
            return paths_to_trial[date_times.index(max(date_times))]
        else:
            raise ValueError(f"Task id {task_id} not found in {self.intan_spike_path}")

    def path_to_spike_file(self, stim_id: int) -> str:
        path_to_trial = self.path_to_trial(stim_id)
        return os.path.join(path_to_trial, "spike.dat")

    def path_to_digital_in(self, stim_id: int) -> str:
        path_to_trial = self.path_to_trial(stim_id)
        return os.path.join(path_to_trial, "digitalin.dat")

    def path_to_notes(self, stim_id: int) -> str:
        path_to_trial = self.path_to_trial(stim_id)
        return os.path.join(path_to_trial, "notes.txt")


def get_current_date() -> str:
    # Get current date
    now = datetime.now()

    # Format the date as "YYYY-MM-DD"
    return now.strftime("%Y-%m-%d")


def filter_spikes_with_epochs(spike_tstamps_for_channels: dict[Channel, list[float]],
                              epochs_for_stim_ids: dict[int, tuple[int, int]], stim_id: int, sample_rate=30000) -> dict[
    Channel, list[float]]:
    filtered_spikes_for_channels = {}
    epoch = epochs_for_stim_ids[stim_id]
    for channel, tstamps in spike_tstamps_for_channels.items():
        passed_filter = []
        for spike_tstamp in tstamps:
            spike_index = int(spike_tstamp * sample_rate)
            if epoch[0] <= spike_index <= epoch[1]:
                passed_filter.append(spike_tstamp)
        filtered_spikes_for_channels[channel] = passed_filter
    return filtered_spikes_for_channels


def find_folders_with_id(root_directory, id: int) -> list[str]:
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


def count_spikes_for_channels(spike_tstamps_for_channels) -> dict[Channel, int]:
    spike_counts_for_channels = {}
    for channel_name, spike_tstamps in spike_tstamps_for_channels.items():
        spike_counts_for_channels[channel_name] = len(spike_tstamps)
    return spike_counts_for_channels

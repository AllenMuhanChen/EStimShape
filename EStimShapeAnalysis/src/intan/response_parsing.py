import os
from datetime import datetime
from typing import Dict, List, Callable

import numpy as np

from intan.channels import Channel
from intan.livenotes import map_task_id_to_epochs_with_livenotes
from intan.marker_channels import epoch_using_marker_channels
from intan.spike_file import fetch_spike_tstamps_from_file
from newga.multi_ga_db_util import MultiGaDbUtil


class ResponseParser:
    """
    Responsible for parsing the spike count from intan files and uploading them to the database as
    a spike count per second for each channel and task
    """

    def __init__(self, base_intan_path: str, db_util: MultiGaDbUtil = None, date_YYYY_MM_DD: str = None):
        if date_YYYY_MM_DD is None:
            self.date = get_current_date_as_YYYY_MM_DD()
        else:
            self.date = date_YYYY_MM_DD
        self.intan_spike_path = base_intan_path
        self.intan_spike_path = os.path.join(self.intan_spike_path, self.date)
        # self.channels = get_channels()
        self.db_util = db_util

    def parse_to_db(self, ga_name: str) -> None:

        stims_to_parse = self.db_util.read_stims_with_no_responses(ga_name)

        task_ids_for_stim_ids = self._read_task_ids_per_stim_id_to_parse_from_db(ga_name, stims_to_parse)

        spike_rates_per_channel_per_task_per_stim = self.parse_spike_rate_per_channel_from(task_ids_for_stim_ids)

        self.write_to_db(spike_rates_per_channel_per_task_per_stim)

    def write_to_db(self, spike_rates_per_channel_per_task_for_stims):
        insert_data = []
        for stim_id, spike_rates_per_channel_for_tasks in spike_rates_per_channel_per_task_for_stims.items():
            for task_id, spikes_per_second_for_channels in spike_rates_per_channel_for_tasks.items():
                for channel, spikes_per_second in spikes_per_second_for_channels.items():
                    row = (stim_id, task_id, channel.value, spikes_per_second)
                    insert_data.append(row)

        self.db_util.add_channel_responses_in_batch(insert_data)

    def _read_task_ids_per_stim_id_to_parse_from_db(self, ga_name, stims_to_parse) -> Dict[int, List[int]]:
        task_ids_for_stim_ids: Dict[int, List[int]] = {}
        for stim_id in stims_to_parse:
            task_ids = self.db_util.read_task_done_ids_for_stim_id(ga_name, stim_id)
            task_ids_for_stim_ids[stim_id] = task_ids
        return task_ids_for_stim_ids

    def parse_spike_rate_per_channel_from(self, task_ids_for_stim_ids: Dict[int, List[int]]) -> Dict[int, Dict[int, Dict[Channel, float]]]:
        spike_rates_per_channel_per_task_for_stims = {}
        for stim_id, task_ids in task_ids_for_stim_ids.items():
            spike_rates_per_channel_for_tasks = self._parse_spike_rates_for_task_ids(task_ids)
            spike_rates_per_channel_per_task_for_stims[stim_id] = spike_rates_per_channel_for_tasks
        return spike_rates_per_channel_per_task_for_stims

    def _parse_spike_rates_for_task_ids(self, task_ids: List[int]) -> Dict[int, Dict[Channel, float]]:
        # For each task_id, parse the spike counts
        spike_rates_per_channel_for_tasks = {}
        for task_id in task_ids:
            spike_rates_per_channel_for_tasks[task_id] = self._parse_spike_rate_per_channel_for_task(task_id)
        return spike_rates_per_channel_for_tasks

    def _parse_spike_rate_per_channel_for_task(self, task_id) -> dict[Channel, float]:
        spike_tstamps_for_channels = fetch_spike_tstamps_from_file(self._path_to_spike_file(task_id))
        stim_epochs_from_markers = epoch_using_marker_channels(self._path_to_digital_in(task_id))
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(self._path_to_notes(task_id),
                                                                   stim_epochs_from_markers)
        spikes_for_channels = filter_spikes_with_epochs(spike_tstamps_for_channels, epochs_for_task_ids, task_id)
        spikes_per_second_for_channels = calculate_spikes_per_second_for_channels(spikes_for_channels,
                                                                                  epochs_for_task_ids)
        return spikes_per_second_for_channels

    def _path_to_trial(self, task_id) -> str:
        paths_to_trial = find_folders_with_id(self.intan_spike_path, task_id)
        if len(paths_to_trial) == 1:
            return paths_to_trial[0]
        elif len(paths_to_trial) > 1:
            # find the most recent one based on timestamps on files
            date_times = [date_time_for_folder(path) for path in paths_to_trial]
            return paths_to_trial[date_times.index(max(date_times))]
        else:
            raise ValueError(f"Task id {task_id} not found in {self.intan_spike_path}")

    def _path_to_spike_file(self, stim_id: int) -> str:
        path_to_trial = self._path_to_trial(stim_id)
        return os.path.join(path_to_trial, "spike.dat")

    def _path_to_digital_in(self, stim_id: int) -> str:
        path_to_trial = self._path_to_trial(stim_id)
        return os.path.join(path_to_trial, "digitalin.dat")

    def _path_to_notes(self, stim_id: int) -> str:
        path_to_trial = self._path_to_trial(stim_id)
        return os.path.join(path_to_trial, "notes.txt")

    def calculate_spike_count_for_channels(self, spikes_for_channels):
        spike_count_for_channels = {}
        for channel, spikes in spikes_for_channels.items():
            spike_count_for_channels[channel] = len(spikes)
        return spike_count_for_channels



def get_current_date_as_YYYY_MM_DD() -> str:
    # Get current date
    now = datetime.now()

    # Format the date as "YYYY-MM-DD"
    return now.strftime("%Y-%m-%d")


def filter_spikes_with_epochs(spike_tstamps_for_channels: dict[Channel, list[float]],
                              epochs_for_task_ids: dict[int, tuple[int, int]], task_id: int, sample_rate=30000) -> dict[
    Channel, list[float]]:
    filtered_spikes_for_channels = {}
    epoch = epochs_for_task_ids[task_id]
    for channel, tstamps in spike_tstamps_for_channels.items():
        passed_filter = []
        for spike_tstamp in tstamps:
            spike_index = int(spike_tstamp * sample_rate)
            if epoch[0] <= spike_index <= epoch[1]:
                passed_filter.append(spike_tstamp)
        filtered_spikes_for_channels[channel] = passed_filter
    return filtered_spikes_for_channels


def calculate_spikes_per_second_for_channels(spikes_for_channels, epochs_for_stim_ids,
                                             sample_rate=30000) -> dict[Channel, float]:
    spikes_per_second_for_channels = {}
    for stim_id, epoch in epochs_for_stim_ids.items():
        for channel, spikes in spikes_for_channels.items():
            spikes_per_second_for_channels[channel] = len(spikes) / (epoch[1]/sample_rate - epoch[0]/sample_rate)
    return spikes_per_second_for_channels


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

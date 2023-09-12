import os
from typing import Dict, List

from compile.task.task_field import TaskField
from intan import spike_file, response_parsing
from intan.channels import Channel
from intan.livenotes import map_task_id_to_epochs_with_livenotes
from intan.marker_channels import epoch_using_marker_channels
from intan.response_parsing import get_current_date_as_YYYY_MM_DD, filter_spikes_with_epochs
import os
import re


class SpikeTimesForChannelsField(TaskField):
    def __init__(self, intan_data_path: str, name: str = "SpikeTimes"):
        super().__init__(name)
        self.intan_data_path = intan_data_path

    def get(self, task_id: int) -> dict[Channel, list[float]] | None:
        matching_intan_file_paths = find_matching_directories(self.intan_data_path, task_id)
        if len(matching_intan_file_paths) == 0:
            return None
        intan_file_path = matching_intan_file_paths[-1]
        spike_path = os.path.join(intan_file_path, "spike.dat")
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path = os.path.join(intan_file_path, "notes.txt")

        spike_tstamps_for_channels, sample_rate = spike_file.fetch_spike_tstamps_from_file(spike_path)

        stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(notes_path,
                                                                   stim_epochs_from_markers)
        spikes_for_channels = response_parsing.filter_spikes_with_epochs(spike_tstamps_for_channels,
                                                                         epochs_for_task_ids, task_id,
                                                                         sample_rate=sample_rate)
        return spikes_for_channels


class EpochStartStopField(TaskField):
    #TODO: clean up a bit, we're duplicating the epoch retrieval between this and SpikeTimesForChannelsField
    def __init__(self, intan_data_path: str, name: str = "EpochStartStop"):
        super().__init__(name)
        self.intan_data_path = intan_data_path

    def get(self, task_id: int) -> tuple[float, float] | None:
        matching_intan_file_paths = find_matching_directories(self.intan_data_path, task_id)
        if len(matching_intan_file_paths) == 0:
            return None
        intan_file_path = matching_intan_file_paths[-1]
        spike_path = os.path.join(intan_file_path, "spike.dat")
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path = os.path.join(intan_file_path, "notes.txt")

        if len(matching_intan_file_paths) == 0:
            return None

        _, sample_rate = spike_file.fetch_spike_tstamps_from_file(spike_path)
        stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(notes_path,
                                                                   stim_epochs_from_markers)
        epoch = epochs_for_task_ids[task_id]
        epoch_start = epoch[0] / sample_rate
        epoch_stop = epoch[1] / sample_rate
        return epoch_start, epoch_stop


def find_matching_directories(root_folder: str, target_number: int) -> list:
    """
    Search through a folder to find directories that start with the given target_number.

    Parameters:
        root_folder (str): The path of the folder to search in.
        target_number (str): The target number to search for.

    Returns:
        list: A list of full directory paths that match the target_number.
    """
    matching_dirs = []
    for dirname in os.listdir(root_folder):
        if re.match(f'^{str(target_number)}_', dirname):
            full_path = os.path.join(root_folder, dirname)
            matching_dirs.append(full_path)

    return matching_dirs

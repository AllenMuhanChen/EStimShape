import os

from compile.task.task_field import TaskField
from intan import spike_file
from intan.livenotes import map_task_id_to_epochs_with_livenotes
from intan.marker_channels import epoch_using_marker_channels
from intan.response_parsing import get_current_date_as_YYYY_MM_DD
import os
import re


class ResponseField(TaskField):
    def __init__(self, intan_base_path, name: str = "Response"):
        super().__init__(name)
        intan_base_path = intan_base_path
        date = get_current_date_as_YYYY_MM_DD()
        self.intan_data_path = os.path.join(intan_base_path, date)

    def get(self, task_id: int) -> str:
        intan_file_path = self.find_matching_directories(self.intan_data_path, task_id)
        intan_file_path = intan_file_path[0]
        spike_path = os.path.join(intan_file_path, "spike.dat")
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path = os.path.join(intan_file_path, "notes.txt")

        spike_tstamps_for_channels, sample_rate = spike_file.fetch_spike_tstamps_from_file(spike_path)
        stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path)
        epoch = stim_epochs_from_markers[0] # There should only be one epoch in Julie's experiment.


    def find_matching_directories(self, root_folder: str, target_number: int) -> list:
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

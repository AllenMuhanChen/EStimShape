import os
from dataclasses import dataclass

from intan import spike_file
from intan.livenotes import map_unique_task_id_to_epochs_with_livenotes
from intan.marker_channels import epoch_using_marker_channels
from intan.spike_file import fetch_spike_tstamps_from_file


@dataclass
class OneFileParser:

    def parse(self, intan_file_path: str):
        spike_path = os.path.join(intan_file_path, "spike.dat")
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path = os.path.join(intan_file_path, "notes.txt")

        spike_tstamps_for_channels, sample_rate = fetch_spike_tstamps_from_file(intan_file_path)
        stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path)
        epochs_for_task_ids = map_unique_task_id_to_epochs_with_livenotes(notes_path,
                                                                          stim_epochs_from_markers)
import os
from dataclasses import dataclass

from intan.livenotes import map_task_id_to_epochs_with_livenotes
from intan.marker_channels import epoch_using_marker_channels
from intan.spike_file import fetch_spike_tstamps_from_file


@dataclass
class OneFileParser:

    def parse(self, intan_file_path: str):
        spike_path = os.path.join(intan_file_path, "spike.dat")
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path = os.path.join(intan_file_path, "notes.txt")

        spike_tstamps_for_channels, sample_rate = fetch_spike_tstamps_from_file(spike_path)
        stim_epochs_from_markers = epoch_using_marker_channels(digital_in_path)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(notes_path,
                                                                          stim_epochs_from_markers)

        filtered_spikes_for_channels_by_task_id = {}
        epoch_start_stop_times_by_task_id = {}
        for task_id, epoch in epochs_for_task_ids.items():
            filtered_spikes_for_channels = {}
            for channel, tstamps in spike_tstamps_for_channels.items():
                passed_filter = []
                for spike_tstamp in tstamps:
                    spike_index = int(spike_tstamp * sample_rate)
                    if epoch[0] <= spike_index <= epoch[1]:
                        passed_filter.append(spike_tstamp)
                filtered_spikes_for_channels[channel] = passed_filter

            epoch_start = epoch[0] / sample_rate
            epoch_end = epoch[1] / sample_rate
            epoch_start_stop_times_by_task_id[task_id] = (epoch_start, epoch_end)
            filtered_spikes_for_channels_by_task_id[task_id] = filtered_spikes_for_channels
        return filtered_spikes_for_channels_by_task_id, epoch_start_stop_times_by_task_id
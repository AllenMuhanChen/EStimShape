import os
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

import numpy as np
from scipy.signal import butter, sosfiltfilt, decimate

from clat.intan.amplifiers import read_amplifier_data
from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import epoch_using_combined_marker_channels


@dataclass
class OneFileLFPParser:
    sample_rate: int
    amplifier_channels: List[dict]
    seconds_before_epoch: float = 0.2
    seconds_after_epoch: float = 0.2
    lowpass_cutoff: float = 250.0
    filter_order: int = 3
    target_sample_rate: int = 1000

    def parse(self, intan_file_path: str) -> Tuple[
        Dict[int, Optional[Dict[str, np.ndarray]]],
        Dict[int, Optional[Tuple[float, float]]],
        int
    ]:
        """
        Returns epoched LFP waveforms by channel by task_id,
        epoch start/stop times by task_id, and the sample rate.

        Returns:
            lfp_by_channel_by_task_id: Dict[taskId, Dict[Channel, np.ndarray]]
                Each np.ndarray is the voltage waveform segment (in microvolts)
                from (epoch_start - seconds_before) to (epoch_end + seconds_after).
            epoch_start_stop_times_by_task_id: Dict[taskId, Tuple[StartSeconds, EndSeconds]]
            sample_rate: int
        """
        amplifier_path = os.path.join(intan_file_path, "amplifier.dat")
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path = os.path.join(intan_file_path, "notes.txt")

        # Read full continuous data: Dict[Channel, np.ndarray]
        channel_to_data = read_amplifier_data(amplifier_path, self.amplifier_channels)

        # Low-pass filter each channel for LFP extraction (250 Hz, 3rd-order Butterworth)
        sos = butter(self.filter_order, self.lowpass_cutoff, btype='low',
                     fs=self.sample_rate, output='sos')
        for channel in channel_to_data:
            channel_to_data[channel] = sosfiltfilt(sos, channel_to_data[channel])

        # Downsample to target_sample_rate (e.g. 30kHz -> 1kHz = factor of 30)
        downsample_factor = int(self.sample_rate / self.target_sample_rate)
        if downsample_factor > 1:
            for channel in channel_to_data:
                # Use decimate with fir filter since we already applied our own anti-alias filter
                channel_to_data[channel] = decimate(
                    channel_to_data[channel], downsample_factor, ftype='fir', zero_phase=True
                )
        lfp_sample_rate = self.sample_rate // downsample_factor if downsample_factor > 1 else self.sample_rate

        # Get epoch indices from marker channels + livenotes
        stim_epochs_from_markers = epoch_using_combined_marker_channels(
            digital_in_path, false_negative_correction_duration=2
        )
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(
            notes_path, stim_epochs_from_markers,
            require_trial_complete=False,
            is_output_first_instance=False
        )

        lfp_by_channel_by_task_id = {}
        epoch_start_stop_times_by_task_id = {}

        for task_id, epoch_indices in epochs_for_task_ids.items():
            print(f"Epoching LFP for task_id: {task_id}")

            if epoch_indices is None:
                epoch_start_stop_times_by_task_id[task_id] = None
                lfp_by_channel_by_task_id[task_id] = None
                continue

            epoch_start_seconds = epoch_indices[0] / self.sample_rate
            epoch_end_seconds = epoch_indices[1] / self.sample_rate

            # Convert time window to sample indices at downsampled rate
            window_start_sample = int((epoch_start_seconds - self.seconds_before_epoch) * lfp_sample_rate)
            window_end_sample = int((epoch_end_seconds + self.seconds_after_epoch) * lfp_sample_rate)

            # Clamp to valid range
            window_start_sample = max(0, window_start_sample)

            lfp_for_channels = {}
            for channel, data in channel_to_data.items():
                clamped_end = min(window_end_sample, len(data))
                lfp_for_channels[channel] = data[window_start_sample:clamped_end]

            epoch_start_stop_times_by_task_id[task_id] = (epoch_start_seconds, epoch_end_seconds)
            lfp_by_channel_by_task_id[task_id] = lfp_for_channels

        return lfp_by_channel_by_task_id, epoch_start_stop_times_by_task_id, lfp_sample_rate
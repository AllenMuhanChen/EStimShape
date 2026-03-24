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

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def parse(self, intan_file_path: str) -> Tuple[
        Dict[int, Optional[Dict[str, np.ndarray]]],
        Dict[int, Optional[Tuple[float, float]]],
        int
    ]:
        """
        Returns epoched LFP waveforms by channel by task_id,
        epoch start/stop times by task_id, and the (downsampled) sample rate.

        Returns:
            lfp_by_channel_by_task_id: Dict[taskId, Dict[Channel, np.ndarray]]
            epoch_start_stop_times_by_task_id: Dict[taskId, Tuple[start_s, end_s]]
            lfp_sample_rate: int
        """
        channel_to_data, lfp_sample_rate, epochs_for_task_ids = \
            self._load_filtered_data(intan_file_path)

        lfp_by_channel_by_task_id = {}
        epoch_start_stop_times_by_task_id = {}

        for task_id, epoch_indices in epochs_for_task_ids.items():
            print(f"Epoching LFP for task_id: {task_id}")

            if epoch_indices is None:
                epoch_start_stop_times_by_task_id[task_id] = None
                lfp_by_channel_by_task_id[task_id] = None
                continue

            epoch_start_s = epoch_indices[0] / self.sample_rate
            epoch_end_s   = epoch_indices[1] / self.sample_rate

            window_start = max(0, int((epoch_start_s - self.seconds_before_epoch) * lfp_sample_rate))
            window_end   = int((epoch_end_s + self.seconds_after_epoch) * lfp_sample_rate)

            lfp_for_channels = {}
            for channel, data in channel_to_data.items():
                lfp_for_channels[channel] = data[window_start:min(window_end, len(data))]

            epoch_start_stop_times_by_task_id[task_id] = (epoch_start_s, epoch_end_s)
            lfp_by_channel_by_task_id[task_id] = lfp_for_channels

        return lfp_by_channel_by_task_id, epoch_start_stop_times_by_task_id, lfp_sample_rate

    def parse_iti(
        self,
        intan_file_path: str,
        min_iti_duration: float,
        start_padding: float,
        end_padding: float,
    ) -> Tuple[
        Dict[int, Dict[str, np.ndarray]],
        Dict[int, Tuple[float, float]],
        int
    ]:
        """
        Parse inter-trial interval (ITI) windows from the continuous LFP signal.

        For each gap between consecutive trial epochs, a window is extracted
        starting at (epoch_end + start_padding) and ending at
        (next_epoch_start - end_padding).  Gaps whose padded duration is less
        than min_iti_duration are discarded.

        Parameters
        ----------
        intan_file_path : str
        min_iti_duration : float
            Minimum required duration (seconds) of the padded ITI window.
            Gaps shorter than this after applying padding are skipped.
        start_padding : float
            Seconds to skip after the end of the preceding trial epoch.
        end_padding : float
            Seconds to skip before the start of the following trial epoch.

        Returns
        -------
        iti_lfp_by_channel_by_idx : Dict[int, Dict[Channel, np.ndarray]]
            ITI windows keyed by integer index (0, 1, 2 ...) in temporal order.
        iti_time_windows_by_idx : Dict[int, Tuple[float, float]]
            (window_start_s, window_end_s) for each ITI, same keys.
        lfp_sample_rate : int
        """
        channel_to_data, lfp_sample_rate, epochs_for_task_ids = \
            self._load_filtered_data(intan_file_path)

        # Collect valid epoch boundaries in seconds, sorted by start time
        valid_epochs = []
        for task_id, epoch_indices in epochs_for_task_ids.items():
            if epoch_indices is None:
                continue
            start_s = epoch_indices[0] / self.sample_rate
            end_s   = epoch_indices[1] / self.sample_rate
            valid_epochs.append((start_s, end_s))

        valid_epochs.sort(key=lambda e: e[0])

        # Find gaps between consecutive epochs
        iti_lfp_by_channel_by_idx = {}
        iti_time_windows_by_idx = {}
        iti_idx = 0

        for i in range(len(valid_epochs) - 1):
            gap_start_s = valid_epochs[i][1]     + start_padding
            gap_end_s   = valid_epochs[i + 1][0] - end_padding

            if (gap_end_s - gap_start_s) < min_iti_duration:
                continue

            window_start = max(0, int(gap_start_s * lfp_sample_rate))
            window_end   = int(gap_end_s * lfp_sample_rate)

            iti_for_channels = {}
            for channel, data in channel_to_data.items():
                iti_for_channels[channel] = data[window_start:min(window_end, len(data))]

            iti_lfp_by_channel_by_idx[iti_idx]      = iti_for_channels
            iti_time_windows_by_idx[iti_idx]         = (gap_start_s, gap_end_s)
            iti_idx += 1

        print(f"Found {iti_idx} ITI windows (min_duration={min_iti_duration}s, "
              f"start_padding={start_padding}s, end_padding={end_padding}s)")

        return iti_lfp_by_channel_by_idx, iti_time_windows_by_idx, lfp_sample_rate

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _load_filtered_data(
        self, intan_file_path: str
    ) -> Tuple[Dict, int, Dict]:
        """
        Load the full continuous amplifier data, apply LFP low-pass filter,
        and downsample.  Also parses epoch markers and livenotes.

        Returns
        -------
        channel_to_data : Dict[Channel, np.ndarray]  (downsampled, filtered)
        lfp_sample_rate : int
        epochs_for_task_ids : Dict[task_id, Optional[Tuple[int, int]]]
            Epoch boundary indices in the *original* (pre-downsample) sample rate.
        """
        amplifier_path  = os.path.join(intan_file_path, "amplifier.dat")
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path      = os.path.join(intan_file_path, "notes.txt")

        channel_to_data = read_amplifier_data(amplifier_path, self.amplifier_channels)

        sos = butter(self.filter_order, self.lowpass_cutoff, btype='low',
                     fs=self.sample_rate, output='sos')
        for channel in channel_to_data:
            channel_to_data[channel] = sosfiltfilt(sos, channel_to_data[channel])

        downsample_factor = int(self.sample_rate / self.target_sample_rate)
        if downsample_factor > 1:
            for channel in channel_to_data:
                channel_to_data[channel] = decimate(
                    channel_to_data[channel], downsample_factor,
                    ftype='fir', zero_phase=True
                )
        lfp_sample_rate = self.sample_rate // downsample_factor if downsample_factor > 1 else self.sample_rate

        stim_epochs_from_markers = epoch_using_combined_marker_channels(
            digital_in_path, false_negative_correction_duration=2
        )
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(
            notes_path, stim_epochs_from_markers,
            require_trial_complete=False,
            is_output_first_instance=False
        )

        return channel_to_data, lfp_sample_rate, epochs_for_task_ids
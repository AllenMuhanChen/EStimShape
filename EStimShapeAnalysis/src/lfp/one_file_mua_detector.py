"""
Multi-Unit Activity (MUA) detector from raw broadband amplifier data.

Implements the spike detection method from Davis et al. (2023) eLife 12:e84512:
    - High-pass filter at 500 Hz
    - Sliding 1-second standard deviation window
    - Threshold crossings at ±4 SD (both polarities)
    - 1 ms refractory period to avoid double-counting

This replaces the dependency on pre-computed spike.dat files (from Intan software)
with detection directly from the raw amplifier waveforms, matching the paper's method.

Returns data in the same format as OneFileParser (spike_times_by_channel_by_task_id)
so it can be used as a drop-in replacement.
"""

import bisect
import os

import numpy as np
from scipy.signal import butter, filtfilt

from clat.intan.amplifiers import read_amplifier_data_with_memmap
from clat.intan.channels import Channel
from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import epoch_using_combined_marker_channels



class OneFileMUADetector:
    """
    Detects multi-unit activity (MUA) from raw broadband amplifier data
    and epochs the detected spike times by task_id.

    Parameters
    ----------
    sample_rate : float
        Original amplifier sample rate (e.g. 30000 Hz).
    amplifier_channels : list
        Channel metadata list from read_data()['amplifier_channels'].
    seconds_before_epoch : float
        Seconds before epoch start to include. Default 0.2.
    seconds_after_epoch : float
        Seconds after epoch end to include. Default 0.2.
    highpass_freq : float
        High-pass filter cutoff in Hz. Default 500.
    filter_order : int
        Butterworth filter order. Default 4.
    threshold_sd : float
        Number of standard deviations for threshold. Default 4.0.
    sd_window_seconds : float
        Sliding window duration for computing local SD. Default 1.0.
    refractory_seconds : float
        Refractory period after each detected spike. Default 0.001 (1 ms).
    """

    def __init__(self, sample_rate: float, amplifier_channels: list,
                 seconds_before_epoch: float = 0.2,
                 seconds_after_epoch: float = 0.2,
                 highpass_freq: float = 500.0,
                 filter_order: int = 4,
                 threshold_sd: float = 4.0,
                 sd_window_seconds: float = 1.0,
                 refractory_seconds: float = 0.001):
        self.sample_rate = sample_rate
        self.amplifier_channels = amplifier_channels
        self.seconds_before_epoch = seconds_before_epoch
        self.seconds_after_epoch = seconds_after_epoch
        self.highpass_freq = highpass_freq
        self.filter_order = filter_order
        self.threshold_sd = threshold_sd
        self.sd_window_seconds = sd_window_seconds
        self.refractory_seconds = refractory_seconds

    def parse(self, intan_file_path: str) -> tuple[
        dict[int, dict], dict[int, tuple[float, float]], float]:
        """
        Detect MUA spikes from raw amplifier data and epoch by task_id.

        Returns the same format as OneFileParser.parse():
            spike_times_by_channel_by_task_id: Dict[taskId, Dict[Channel, list[float]]]
            epoch_start_stop_times_by_task_id: Dict[taskId, Tuple[start_sec, end_sec]]
            sample_rate: float
        """
        # Load raw amplifier data as dict {Channel: data_in_microvolts}
        amplifier_dat_path = os.path.join(intan_file_path, "amplifier.dat")
        channel_to_data = read_amplifier_data_with_memmap(amplifier_dat_path, self.amplifier_channels)

        # Detect spikes on all channels (returns absolute times in seconds)
        print("Detecting MUA spikes from raw amplifier data...")
        spike_times_by_channel = self._detect_all_channels(channel_to_data)

        # Get epoch boundaries from digital markers and livenotes
        digital_in_path = os.path.join(intan_file_path, "digitalin.dat")
        notes_path = os.path.join(intan_file_path, "notes.txt")

        stim_epochs_from_markers = epoch_using_combined_marker_channels(
            digital_in_path, false_negative_correction_duration=2)
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(
            notes_path, stim_epochs_from_markers,
            require_trial_complete=False,
            is_output_first_instance=False)

        # Epoch the spike times
        spike_times_by_channel_by_task_id = {}
        epoch_start_stop_times_by_task_id = {}

        for task_id, epoch_indices in epochs_for_task_ids.items():
            print(f"Epoching task_id: {task_id}")
            if epoch_indices is None:
                spike_times_by_channel_by_task_id[task_id] = None
                epoch_start_stop_times_by_task_id[task_id] = None
                continue

            filtered_spikes_for_channels = {}
            for channel, tstamps in spike_times_by_channel.items():
                start_time = (epoch_indices[0] / self.sample_rate) - self.seconds_before_epoch
                end_time = (epoch_indices[1] / self.sample_rate) + self.seconds_after_epoch
                start_index = bisect.bisect_left(tstamps, start_time)
                end_index = bisect.bisect_right(tstamps, end_time)
                filtered_spikes_for_channels[channel] = tstamps[start_index:end_index]

            epoch_start_seconds = epoch_indices[0] / self.sample_rate
            epoch_end_seconds = epoch_indices[1] / self.sample_rate
            epoch_start_stop_times_by_task_id[task_id] = (epoch_start_seconds, epoch_end_seconds)
            spike_times_by_channel_by_task_id[task_id] = filtered_spikes_for_channels

        return spike_times_by_channel_by_task_id, epoch_start_stop_times_by_task_id, self.sample_rate

    def _detect_all_channels(self, channel_to_data: dict) -> dict:
        """
        Run MUA detection on all channels.

        Parameters
        ----------
        channel_to_data : dict
            {Channel: np.ndarray} mapping from Channel to raw voltage data in microvolts,
            as returned by read_amplifier_data_with_memmap.

        Returns
        -------
        spike_times_by_channel : dict
            {Channel: sorted list of spike times in seconds}
        """
        # Design the high-pass filter once
        nyq = self.sample_rate / 2.0
        high = self.highpass_freq / nyq
        b, a = butter(self.filter_order, high, btype='high')

        spike_times_by_channel = {}

        for channel, raw in channel_to_data.items():
            # Step 1: High-pass filter at 500 Hz (zero-phase)
            filtered = filtfilt(b, a, raw)

            # Step 2: Detect spikes using sliding SD threshold
            spike_samples = self._detect_spikes(filtered)

            # Step 3: Convert sample indices to absolute times in seconds
            spike_times = spike_samples / self.sample_rate

            spike_times_by_channel[channel] = list(spike_times)

            print(f"  Channel {channel}: {len(spike_times)} spikes detected")

        return spike_times_by_channel

    def _detect_spikes(self, filtered_signal: np.ndarray) -> np.ndarray:
        """
        Detect threshold crossings using a sliding SD window.

        Both positive and negative threshold crossings are detected
        (absolute value > threshold_sd * local_sd).

        A 1 ms refractory period is enforced after each detection.

        Parameters
        ----------
        filtered_signal : np.ndarray
            High-pass filtered voltage trace.

        Returns
        -------
        spike_samples : np.ndarray
            Sample indices of detected spikes.
        """
        n_samples = len(filtered_signal)
        window_samples = int(self.sd_window_seconds * self.sample_rate)
        refractory_samples = int(self.refractory_seconds * self.sample_rate)

        # Compute sliding SD using a moving window
        # For efficiency, use a strided/cumulative approach
        local_sd = self._sliding_std(filtered_signal, window_samples)

        # Compute threshold: ±threshold_sd * local_sd
        threshold = self.threshold_sd * local_sd

        # Detect crossings (both polarities)
        abs_signal = np.abs(filtered_signal)
        above_threshold = abs_signal > threshold

        # Find all threshold crossings (rising edges: was below, now above)
        crossings = np.where(np.diff(above_threshold.astype(int)) == 1)[0] + 1

        if len(crossings) == 0:
            return np.array([], dtype=int)

        # For each crossing, find the peak (max absolute value) within the
        # next few samples (1 ms window) to get precise spike time
        peak_window = refractory_samples
        spike_samples = []

        for crossing in crossings:
            window_end = min(crossing + peak_window, n_samples)
            segment = abs_signal[crossing:window_end]
            if len(segment) > 0:
                peak_offset = np.argmax(segment)
                spike_samples.append(crossing + peak_offset)

        spike_samples = np.array(spike_samples, dtype=int)

        # Enforce refractory period
        if len(spike_samples) > 1:
            spike_samples = self._enforce_refractory(spike_samples, refractory_samples)

        return spike_samples

    @staticmethod
    def _sliding_std(signal: np.ndarray, window_samples: int) -> np.ndarray:
        """
        Compute sliding standard deviation using cumulative sum approach.

        For samples near the edges where a full window isn't available,
        uses whatever samples are available (minimum window of window_samples//10).

        Parameters
        ----------
        signal : np.ndarray
            Input signal.
        window_samples : int
            Window size in samples.

        Returns
        -------
        local_std : np.ndarray
            Local standard deviation, same length as signal.
        """
        n = len(signal)

        # Use cumulative sums for O(n) computation
        # Pad signal for the cumsum trick
        cumsum = np.cumsum(signal)
        cumsum2 = np.cumsum(signal ** 2)

        # Insert 0 at the beginning for easier indexing
        cumsum = np.insert(cumsum, 0, 0)
        cumsum2 = np.insert(cumsum2, 0, 0)

        local_std = np.zeros(n)
        half_win = window_samples // 2

        for i in range(n):
            left = max(0, i - half_win)
            right = min(n, i + half_win)
            count = right - left

            if count < 2:
                local_std[i] = 1e-6  # Avoid division by zero
                continue

            s = cumsum[right] - cumsum[left]
            s2 = cumsum2[right] - cumsum2[left]
            mean = s / count
            variance = s2 / count - mean ** 2

            # Numerical stability: variance can be slightly negative due to floating point
            local_std[i] = np.sqrt(max(variance, 0))

        # Prevent zero SD (which would make infinite threshold)
        local_std = np.maximum(local_std, 1e-6)

        return local_std

    @staticmethod
    def _enforce_refractory(spike_samples: np.ndarray, refractory_samples: int) -> np.ndarray:
        """
        Remove spikes that fall within the refractory period of a preceding spike.

        Parameters
        ----------
        spike_samples : np.ndarray
            Sorted array of spike sample indices.
        refractory_samples : int
            Minimum inter-spike interval in samples.

        Returns
        -------
        filtered : np.ndarray
            Spike samples with refractory period enforced.
        """
        kept = [spike_samples[0]]
        for spike in spike_samples[1:]:
            if spike - kept[-1] >= refractory_samples:
                kept.append(spike)
        return np.array(kept, dtype=int)
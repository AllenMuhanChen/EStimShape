import os
import pickle
import glob
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from clat.intan.rhs.load_intan_rhs_format import read_data

from clat.intan.amplifiers import read_amplifier_data
from clat.intan.livenotes import map_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import epoch_using_combined_marker_channels
from scipy.signal import butter, sosfiltfilt, decimate

from src.intan.MultiFileParser import find_files_containing_task_ids, find_all_recording_dirs
from src.intan.one_file_lfp_parsing import OneFileLFPParser
from src.lfp.mua_detection import detect_mua_spikes


class MultiFileLFPParser:
    """
    Given a list of task IDs, parses all Intan files that contain those task IDs
    and returns combined LFP data.

    Analogous to MultiFileParser but for LFP waveforms instead of spikes.

    For each matching directory, reads the RHS file to obtain sample_rate and
    amplifier_channels, constructs a OneFileLFPParser, and calls parse().

    Returns:
        lfp_by_channel_by_task_id: Dict[task_id, Dict[Channel, np.ndarray]]
        epoch_start_stop_times_by_task_id: Dict[task_id, Tuple[float, float]]
        lfp_sample_rate: int

    If to_cache is True:
        - Parsed data is saved to cache_dir as pickle files.
        - On subsequent calls, cached task IDs are loaded from disk; only
          missing task IDs are parsed from the raw Intan files.
    """

    lfp_sample_rate: Optional[int] = None

    def __init__(
        self,
        seconds_before_epoch: float = 0.2,
        seconds_after_epoch: float = 0.2,
        lowpass_cutoff: float = 250.0,
        filter_order: int = 3,
        target_sample_rate: int = 1000,
        to_cache: bool = False,
        cache_dir: Optional[str] = None,
    ):
        self.seconds_before_epoch = seconds_before_epoch
        self.seconds_after_epoch = seconds_after_epoch
        self.lowpass_cutoff = lowpass_cutoff
        self.filter_order = filter_order
        self.target_sample_rate = target_sample_rate
        self.to_cache = to_cache
        self.cache_dir = cache_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        task_ids: List[int],
        intan_files_dir: str,
    ) -> Tuple[Dict[int, Any], Dict[int, Any], int]:
        """
        Parse LFP for the given task IDs across all matching Intan files.

        Returns
        -------
        lfp_by_channel_by_task_id : Dict[task_id, Dict[Channel, np.ndarray] | None]
        epoch_start_stop_times_by_task_id : Dict[task_id, Tuple[float, float] | None]
        lfp_sample_rate : int
        """
        lfp_by_channel_by_task_id: Dict[int, Any] = {}
        epoch_start_stop_times_by_task_id: Dict[int, Any] = {}

        task_id_set = set(task_ids)
        remaining_task_ids = list(task_id_set)

        # Load from cache where available
        if self.to_cache and self.cache_dir is not None:
            cached_lfp, cached_epochs, missing_task_ids = self._load_cache(task_ids)
            lfp_by_channel_by_task_id.update(cached_lfp)
            epoch_start_stop_times_by_task_id.update(cached_epochs)

            if not missing_task_ids:
                return lfp_by_channel_by_task_id, epoch_start_stop_times_by_task_id, self.lfp_sample_rate

            remaining_task_ids = missing_task_ids

        # Find Intan file directories that contain the remaining task IDs
        remaining_set = set(remaining_task_ids)
        matching_dirs = find_files_containing_task_ids(remaining_set, intan_files_dir)

        if not matching_dirs:
            if lfp_by_channel_by_task_id:
                return lfp_by_channel_by_task_id, epoch_start_stop_times_by_task_id, self.lfp_sample_rate
            raise ValueError(f"No Intan files found containing task IDs {task_ids}")

        new_lfp: Dict[int, Any] = {}
        new_epochs: Dict[int, Any] = {}

        for dir_path in matching_dirs:
            file_lfp, file_epochs, file_sr = self._parse_one_dir(dir_path)

            if self.lfp_sample_rate is None:
                self.lfp_sample_rate = file_sr
            elif file_sr != self.lfp_sample_rate:
                raise ValueError(
                    f"Inconsistent LFP sample rates: {self.lfp_sample_rate} vs {file_sr}"
                )

            for task_id, channel_data in file_lfp.items():
                if task_id in remaining_set:
                    lfp_by_channel_by_task_id[task_id] = channel_data
                    epoch_start_stop_times_by_task_id[task_id] = file_epochs[task_id]
                    new_lfp[task_id] = channel_data
                    new_epochs[task_id] = file_epochs[task_id]

        if self.to_cache and self.cache_dir is not None and new_lfp:
            self._cache(new_lfp, new_epochs)

        return lfp_by_channel_by_task_id, epoch_start_stop_times_by_task_id, self.lfp_sample_rate

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_one_dir(self, dir_path: str) -> Tuple[Dict, Dict, int]:
        """Read RHS metadata and parse LFP from a single Intan directory."""
        rhs_path = os.path.join(dir_path, "info.rhs")
        data = read_data(rhs_path)
        sample_rate = data['frequency_parameters']['amplifier_sample_rate']
        amplifier_channels = data['amplifier_channels']
        del data  # free RHS header dict before loading amplifier data

        parser = OneFileLFPParser(
            sample_rate=sample_rate,
            amplifier_channels=amplifier_channels,
            seconds_before_epoch=self.seconds_before_epoch,
            seconds_after_epoch=self.seconds_after_epoch,
            lowpass_cutoff=self.lowpass_cutoff,
            filter_order=self.filter_order,
            target_sample_rate=self.target_sample_rate,
        )
        return parser.parse(dir_path)

    def _cache(self, lfp_by_channel_by_task_id: Dict, epoch_start_stop_times_by_task_id: Dict) -> str:
        if self.cache_dir is None:
            raise ValueError("cache_dir is not set.")

        os.makedirs(self.cache_dir, exist_ok=True)

        sorted_task_ids = sorted(epoch_start_stop_times_by_task_id.keys())
        if not sorted_task_ids:
            raise ValueError("No task IDs in data to cache.")

        filename = f"{sorted_task_ids[0]}_to_{sorted_task_ids[-1]}_parsed_lfp_and_epochs.pkl"
        file_path = os.path.join(self.cache_dir, filename)

        cache_data = {
            'lfp_by_channel_by_task_id': lfp_by_channel_by_task_id,
            'epoch_start_stop_times_by_task_id': epoch_start_stop_times_by_task_id,
            'lfp_sample_rate': self.lfp_sample_rate,
            'task_ids': sorted_task_ids,
        }
        with open(file_path, 'wb') as f:
            pickle.dump(cache_data, f)

        return file_path

    def _load_cache(self, task_ids: List[int]) -> Tuple[Dict, Dict, List[int]]:
        if not os.path.exists(self.cache_dir):
            return {}, {}, list(task_ids)

        cache_files = glob.glob(os.path.join(self.cache_dir, "*_parsed_lfp_and_epochs.pkl"))

        combined_lfp: Dict[int, Any] = {}
        combined_epochs: Dict[int, Any] = {}
        missing_task_ids = list(task_ids)

        for cache_file in cache_files:
            try:
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)

                if self.lfp_sample_rate is None and 'lfp_sample_rate' in cache_data:
                    self.lfp_sample_rate = cache_data['lfp_sample_rate']
                elif (self.lfp_sample_rate is not None
                      and cache_data.get('lfp_sample_rate') != self.lfp_sample_rate):
                    print(
                        f"Warning: sample rate mismatch in {cache_file}. "
                        f"Expected {self.lfp_sample_rate}, "
                        f"got {cache_data.get('lfp_sample_rate')}. Skipping."
                    )
                    continue

                cached_task_ids = set(cache_data.get('task_ids', []))
                lfp_data = cache_data.get('lfp_by_channel_by_task_id', {})
                epoch_data = cache_data.get('epoch_start_stop_times_by_task_id', {})

                for task_id in task_ids:
                    if task_id in cached_task_ids and task_id in lfp_data and task_id in epoch_data:
                        combined_lfp[task_id] = lfp_data[task_id]
                        combined_epochs[task_id] = epoch_data[task_id]
                        if task_id in missing_task_ids:
                            missing_task_ids.remove(task_id)

            except Exception as e:
                print(f"Error reading LFP cache file {cache_file}: {e}")
                continue

        return combined_lfp, combined_epochs, missing_task_ids

    # ------------------------------------------------------------------
    # ITI public API
    # ------------------------------------------------------------------

    def parse_iti(
        self,
        intan_files_dir: str,
        min_iti_duration: float = 0.5,
        start_padding: float = 0.1,
        end_padding: float = 0.1,
        mua_highpass_hz: float = 300.0,
        mua_threshold_rms: float = 4.0,
        mua_refractory_sec: float = 0.001,
    ) -> Tuple[
        Dict[int, Dict],   # iti_lfp_by_idx[iti_idx][channel_key] = np.ndarray
        Dict[int, Dict],   # iti_spike_rate_by_idx[iti_idx][channel_key] = float (Hz)
        Dict[int, Tuple[float, float]],  # iti_time_windows_by_idx[iti_idx] = (start_s, end_s)
        int,               # lfp_sample_rate
    ]:
        """
        Parse LFP waveforms and MUA spike rates for all ITI windows across the session.

        ITIs are identified as gaps between consecutive task epochs within each recording
        file. Windows that span a file boundary are skipped.

        Parameters
        ----------
        intan_files_dir  : Root directory containing all recording subdirectories.
        min_iti_duration : Minimum gap duration (seconds) after padding to keep an ITI.
        start_padding    : Seconds to skip after the preceding trial epoch ends.
        end_padding      : Seconds to skip before the next trial epoch starts.
        mua_highpass_hz  : High-pass cutoff (Hz) for MUA spike detection.
        mua_threshold_rms: Negative threshold multiplier (N × RMS).
        mua_refractory_sec: Refractory period (seconds) for MUA detection.

        Returns
        -------
        iti_lfp_by_idx, iti_spike_rate_by_idx, iti_time_windows_by_idx, lfp_sample_rate
        """
        iti_cache_dir = None
        if self.to_cache and self.cache_dir is not None:
            iti_cache_dir = self.cache_dir.rstrip('/') + '_iti'
            cached = self._load_iti_cache(iti_cache_dir)
            if cached is not None:
                return cached

        recording_dirs = find_all_recording_dirs(intan_files_dir)
        if not recording_dirs:
            raise ValueError(f"No recording directories found under {intan_files_dir}")

        all_lfp: Dict[int, Dict] = {}
        all_rates: Dict[int, Dict] = {}
        all_windows: Dict[int, Tuple[float, float]] = {}
        global_idx = 0

        for dir_path in recording_dirs:
            dir_lfp, dir_rates, dir_windows, sr = self._parse_iti_one_dir(
                dir_path,
                min_iti_duration, start_padding, end_padding,
                mua_highpass_hz, mua_threshold_rms, mua_refractory_sec,
            )
            if self.lfp_sample_rate is None:
                self.lfp_sample_rate = sr
            for local_idx in sorted(dir_windows.keys()):
                all_lfp[global_idx] = dir_lfp[local_idx]
                all_rates[global_idx] = dir_rates[local_idx]
                all_windows[global_idx] = dir_windows[local_idx]
                global_idx += 1

        if iti_cache_dir is not None:
            self._save_iti_cache(iti_cache_dir, all_lfp, all_rates, all_windows)

        print(f"Found {global_idx} ITI windows across {len(recording_dirs)} recording file(s).")
        return all_lfp, all_rates, all_windows, self.lfp_sample_rate

    # ------------------------------------------------------------------
    # ITI private helpers
    # ------------------------------------------------------------------

    def _parse_iti_one_dir(
        self,
        dir_path: str,
        min_iti_duration: float,
        start_padding: float,
        end_padding: float,
        mua_highpass_hz: float,
        mua_threshold_rms: float,
        mua_refractory_sec: float,
    ) -> Tuple[Dict, Dict, Dict, int]:
        """
        Parse ITI LFP + MUA for a single recording directory.

        Returns (lfp_by_local_idx, spike_rate_by_local_idx, windows_by_local_idx, sr)
        """
        rhs_path = os.path.join(dir_path, "info.rhs")
        amplifier_path = os.path.join(dir_path, "amplifier.dat")
        digital_in_path = os.path.join(dir_path, "digitalin.dat")
        notes_path = os.path.join(dir_path, "notes.txt")

        # Read RHS metadata
        rhs_data = read_data(rhs_path)
        raw_sample_rate = rhs_data['frequency_parameters']['amplifier_sample_rate']
        amplifier_channels = rhs_data['amplifier_channels']
        del rhs_data

        # Load full wideband signal
        channel_to_raw = read_amplifier_data(amplifier_path, amplifier_channels)

        # Compute ITI epoch boundaries (in raw sample indices)
        stim_epochs = epoch_using_combined_marker_channels(
            digital_in_path, false_negative_correction_duration=2
        )
        epochs_for_task_ids = map_task_id_to_epochs_with_livenotes(
            notes_path, stim_epochs,
            require_trial_complete=False,
            is_output_first_instance=False,
        )

        # Build sorted list of valid (start_s, end_s) epoch boundaries
        valid_epochs = []
        for epoch_indices in epochs_for_task_ids.values():
            if epoch_indices is None:
                continue
            start_s = epoch_indices[0] / raw_sample_rate
            end_s = epoch_indices[1] / raw_sample_rate
            valid_epochs.append((start_s, end_s))
        valid_epochs.sort(key=lambda e: e[0])

        if len(valid_epochs) < 2:
            return {}, {}, {}, int(raw_sample_rate // (raw_sample_rate // self.target_sample_rate))

        # Compute LFP filter + downsample factor once
        downsample_factor = max(1, int(raw_sample_rate / self.target_sample_rate))
        lfp_sr = raw_sample_rate // downsample_factor
        sos_lpf = butter(self.filter_order, self.lowpass_cutoff,
                         btype='low', fs=raw_sample_rate, output='sos')

        lfp_by_idx: Dict[int, Dict] = {}
        rate_by_idx: Dict[int, Dict] = {}
        windows_by_idx: Dict[int, Tuple[float, float]] = {}
        local_idx = 0

        for i in range(len(valid_epochs) - 1):
            gap_start_s = valid_epochs[i][1] + start_padding
            gap_end_s = valid_epochs[i + 1][0] - end_padding

            if (gap_end_s - gap_start_s) < min_iti_duration:
                continue

            # Raw-sample window
            raw_start = max(0, int(gap_start_s * raw_sample_rate))
            raw_end = int(gap_end_s * raw_sample_rate)

            lfp_channels: Dict = {}
            mua_rates: Dict = {}

            for channel, raw_signal in channel_to_raw.items():
                segment = raw_signal[raw_start:raw_end]
                if len(segment) == 0:
                    continue

                # LFP: low-pass + downsample
                lfp_seg = sosfiltfilt(sos_lpf, segment)
                if downsample_factor > 1:
                    lfp_seg = decimate(lfp_seg, downsample_factor, ftype='fir', zero_phase=True)
                lfp_channels[channel] = lfp_seg

                # MUA spike rate
                spikes = detect_mua_spikes(
                    segment, raw_sample_rate,
                    highpass_hz=mua_highpass_hz,
                    threshold_rms=mua_threshold_rms,
                    refractory_sec=mua_refractory_sec,
                )
                duration = len(segment) / raw_sample_rate
                mua_rates[channel] = len(spikes) / duration if duration > 0 else 0.0

            lfp_by_idx[local_idx] = lfp_channels
            rate_by_idx[local_idx] = mua_rates
            windows_by_idx[local_idx] = (gap_start_s, gap_end_s)
            local_idx += 1

        return lfp_by_idx, rate_by_idx, windows_by_idx, int(lfp_sr)

    def _save_iti_cache(self, iti_cache_dir: str, lfp: Dict, rates: Dict, windows: Dict) -> None:
        os.makedirs(iti_cache_dir, exist_ok=True)
        cache_path = os.path.join(iti_cache_dir, "iti_parsed.pkl")
        with open(cache_path, 'wb') as f:
            pickle.dump({
                'lfp': lfp, 'rates': rates, 'windows': windows,
                'lfp_sample_rate': self.lfp_sample_rate,
            }, f)

    def _load_iti_cache(self, iti_cache_dir: str):
        cache_path = os.path.join(iti_cache_dir, "iti_parsed.pkl")
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            if self.lfp_sample_rate is None:
                self.lfp_sample_rate = data.get('lfp_sample_rate')
            print(f"Loaded ITI data from cache: {len(data['windows'])} windows.")
            return data['lfp'], data['rates'], data['windows'], self.lfp_sample_rate
        except Exception as e:
            print(f"Failed to load ITI cache: {e}")
            return None

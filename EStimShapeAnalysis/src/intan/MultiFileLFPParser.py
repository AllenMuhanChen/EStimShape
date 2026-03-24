import os
import pickle
import glob
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
from clat.intan.rhs.load_intan_rhs_format import read_data

from src.intan.MultiFileParser import find_files_containing_task_ids
from src.intan.one_file_lfp_parsing import OneFileLFPParser


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

import os
from datetime import datetime
from typing import Dict, List, Callable, Protocol

import numpy as np
import pandas as pd
import xmltodict

from clat.intan.channels import Channel
from clat.intan.livenotes import map_unique_task_id_to_epochs_with_livenotes
from clat.intan.marker_channels import epoch_using_marker_channels
from clat.intan.one_file_spike_parsing import OneFileParser
from clat.intan.spike_file import fetch_spike_tstamps_from_file
from clat.util.connection import Connection
from src.lfp.spike_waveform_features import highpass_filter
from src.pga.multi_ga_db_util import MultiGaDbUtil


class ResponseParser(Protocol):
    def parse_to_db(self, ga_name: str) -> None:
        pass


def _count_mad_negative_spikes(segment: np.ndarray, threshold: float,
                               refractory_samples: int) -> int:
    """Count negative-going crossings of `threshold` (< 0) in `segment`, snapping
    to the local trough and enforcing a refractory period. Mirrors the MAD/RMS
    detector used in the offline analysis (negative crossings only)."""
    if segment.size < 2:
        return 0
    below = segment < threshold
    crossings = np.where(np.diff(below.astype(np.int8)) == 1)[0] + 1
    if len(crossings) == 0:
        return 0
    n = len(segment)
    troughs = []
    for c in crossings:
        window_end = min(c + refractory_samples, n)
        troughs.append(c + int(np.argmin(segment[c:window_end])))
    kept = [troughs[0]]
    for s in troughs[1:]:
        if s - kept[-1] >= refractory_samples:
            kept.append(s)
    return len(kept)


def _read_amplifier_header(intan_dir: str):
    """Return (sample_rate, amplifier_channels) from info.rhd (or .rhs)."""
    rhd_path = os.path.join(intan_dir, "info.rhd")
    rhs_path = os.path.join(intan_dir, "info.rhs")
    if os.path.exists(rhd_path):
        from clat.intan.rhd.load_intan_rhd_format import read_data
        header = read_data(rhd_path)
    elif os.path.exists(rhs_path):
        from clat.intan.rhs.load_intan_rhs_format import read_data
        header = read_data(rhs_path)
    else:
        raise FileNotFoundError(f"No info.rhd/info.rhs header in {intan_dir}")
    return (header['frequency_parameters']['amplifier_sample_rate'],
            header['amplifier_channels'])


class IntanResponseParser(ResponseParser):
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
        intan_dirs_for_this_gen = self.find_matching_folders(ga_name)
        print(f"Found {len(intan_dirs_for_this_gen)} matching folders for GA {ga_name}")

        if not intan_dirs_for_this_gen:
            print("No matching folders found.")
            print("Check if the gen_id and experiment_id on the intan file matches what InternalState says.")
            return

        # Parse all the intan files for this generation
        spike_tstamps_for_channels_by_task_id = {}
        epoch_start_stop_by_task_id = {}
        sample_rate = None
        for intan_dir in intan_dirs_for_this_gen:
            parser = OneFileParser()
            (local_spike_tstamps_for_channels_by_task_id,
             local_epoch_start_stop_by_task_id,
             local_sample_rate) = parser.parse(intan_dir)
            spike_tstamps_for_channels_by_task_id.update(local_spike_tstamps_for_channels_by_task_id)
            epoch_start_stop_by_task_id.update(local_epoch_start_stop_by_task_id)
            if sample_rate is None:
                sample_rate = local_sample_rate
            elif sample_rate != local_sample_rate:
                raise ValueError("Sample rates do not match")


        stims_to_parse = self.db_util.read_stims_with_no_responses(ga_name)
        task_ids_for_stim_ids = self._read_task_ids_per_stim_id_to_parse_from_db(ga_name, stims_to_parse)

        df_spike_rates = self._process_data_to_df(spike_tstamps_for_channels_by_task_id, epoch_start_stop_by_task_id,
                                                  task_ids_for_stim_ids, sample_rate)

        df_spike_rates = df_spike_rates.dropna()

        self._write_to_db(df_spike_rates)

    def _process_data_to_df(self, spikes, epochs, task_ids_for_stim_ids, sample_rate):
        # Build reverse lookup once: task_id → stim_id
        # Avoids the O(n_stims) linear scan that _find_stim_id_for_task does per task.
        task_to_stim = {
            task_id: stim_id
            for stim_id, task_ids in task_ids_for_stim_ids.items()
            for task_id in task_ids
        }

        data = []
        for task_id, spikes_for_channels in spikes.items():
            stim_id = task_to_stim.get(task_id)
            epoch = epochs[task_id]
            epoch_start, epoch_end = epoch[0], epoch[1]
            epoch_duration = epoch_end - epoch_start

            if spikes_for_channels is None:
                print("No spike data for task_id ", task_id)
                continue

            for channel, spike_times in spikes_for_channels.items():
                times = np.asarray(spike_times)
                spike_count = int(np.sum((times >= epoch_start) & (times <= epoch_end)))
                spike_rate = spike_count / epoch_duration
                data.append({
                    'stim_id': stim_id,
                    'task_id': task_id,
                    'channel': channel.value,
                    'spike_rate': spike_rate,
                })

        return pd.DataFrame(data)

    def _find_stim_id_for_task(self, task_ids_for_stim_ids, task_id):
        # Search through the dictionary to find the stim_id that contains the task_id
        for stim_id, task_ids in task_ids_for_stim_ids.items():
            if task_id in task_ids:
                return stim_id
        print(f"Task ID {task_id} not found in any stim_id")
        return None



    def _write_to_db(self, df):
        # Convert DataFrame rows to a list of tuples for SQL execution
        insert_data = [tuple(row) for row in
                       df[['stim_id', 'task_id', 'channel', 'spike_rate']].itertuples(index=False)]
        self.db_util.add_channel_responses_in_batch(insert_data)

    def find_matching_folders(self, ga_name: str):
        current_experiment_id = self.db_util.read_current_experiment_id(ga_name)
        current_gen_id = self.db_util.read_ready_gas_and_generations_info().get(ga_name)
        matching_folders = []

        # Walk through the directory structure
        for root, dirs, files in os.walk(self.intan_spike_path):
            for dir_name in dirs:
                # Parse directory name to extract IDs
                parts = dir_name.split('_')
                if len(parts) >= 5:
                    experiment_id = int(parts[0])
                    gen_id = int(parts[1])

                    # Check if this directory matches the current experiment and generation IDs
                    if experiment_id == current_experiment_id and gen_id == current_gen_id:
                        full_path = os.path.join(root, dir_name)
                        matching_folders.append(full_path)

        return matching_folders

    def _read_task_ids_per_stim_id_to_parse_from_db(self, ga_name, stims_to_parse) -> Dict[int, List[int]]:
        '''
        returns: Dict[stim_id, List[task_id]]
        '''
        task_ids_for_stim_ids: Dict[int, List[int]] = {}
        for stim_id in stims_to_parse:
            task_ids = self.db_util.read_task_done_ids_by_stim_id(ga_name, stim_id)
            task_ids_for_stim_ids[stim_id] = task_ids
        return task_ids_for_stim_ids

    def _parse_spike_rate_per_channel_from(self, task_ids_for_stim_ids: Dict[int, List[int]]) -> Dict[
        int, Dict[int, Dict[Channel, float]]]:
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
        spike_tstamps_for_channels, sample_rate = fetch_spike_tstamps_from_file(self._path_to_spike_file(task_id))
        stim_epochs_from_markers = epoch_using_marker_channels(self._path_to_digital_in(task_id))
        epochs_for_task_ids = map_unique_task_id_to_epochs_with_livenotes(self._path_to_notes(task_id),
                                                                          stim_epochs_from_markers)
        spikes_for_channels = filter_spikes_with_epochs(spike_tstamps_for_channels, epochs_for_task_ids, task_id,
                                                        sample_rate=sample_rate)
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


class MuaIntanResponseParser(IntanResponseParser):
    """
    Runs the standard spike.dat parse (writing ChannelResponses, unchanged) AND a
    second pass that re-detects MUA from the raw wideband (amplifier.dat) using a
    -k x MAD negative threshold refreshed every `block_size` task_ids, writing the
    per-trial per-channel rates to MUAChannelResponses under `mua_metric`.

    Epochs and task alignment are taken from OneFileParser (the same source the
    spike.dat parse uses), so MUA responses map to task_ids identically.
    """

    def __init__(self, base_intan_path, db_util: MultiGaDbUtil = None,
                 date_YYYY_MM_DD: str = None, *,
                 mua_metric: str = "mad_k4_block100",
                 threshold_k: float = 4.0,
                 block_size: int = 100,
                 highpass_hz: float = 300.0,
                 refractory_sec: float = 0.001):
        super().__init__(base_intan_path, db_util, date_YYYY_MM_DD)
        self.mua_metric = mua_metric
        self.threshold_k = threshold_k
        self.block_size = block_size
        self.highpass_hz = highpass_hz
        self.refractory_sec = refractory_sec
        if self.db_util is not None:
            self.db_util.create_mua_channel_responses_table_if_not_exists()

    def parse_to_db(self, ga_name: str) -> None:
        # 1) Unchanged spike.dat parse -> ChannelResponses
        super().parse_to_db(ga_name)
        # 2) Wideband MUA parse -> MUAChannelResponses
        self._parse_mua_to_db(ga_name)

    def _parse_mua_to_db(self, ga_name: str) -> None:
        folders = self.find_matching_folders(ga_name)
        if not folders:
            print("MUA parse: no matching Intan folders found.")
            return

        stims_to_parse = self.db_util.read_stims_with_no_mua_responses(ga_name, self.mua_metric)
        if not stims_to_parse:
            print("MUA parse: no stims left to parse for metric", self.mua_metric)
            return
        task_to_stim = {}
        for stim_id in stims_to_parse:
            for task_id in self.db_util.read_task_done_ids_by_stim_id(ga_name, stim_id):
                task_to_stim[task_id] = stim_id

        rows = []
        for folder in folders:
            _, epochs_by_task, sample_rate = OneFileParser().parse(folder)
            rows.extend(self._detect_mua_rows_for_folder(
                folder, epochs_by_task, sample_rate, task_to_stim))

        rows = [r for r in rows if r[4] == r[4]]  # drop NaN rates
        if rows:
            self.db_util.add_mua_channel_responses_in_batch(rows)
        print(f"MUA parse: wrote {len(rows)} MUAChannelResponses rows "
              f"(metric={self.mua_metric}).")

    def _detect_mua_rows_for_folder(self, intan_dir, epochs_by_task, sample_rate,
                                    task_to_stim) -> list:
        from clat.intan.amplifiers import read_amplifier_data_with_memmap

        _sr_header, amplifier_channels = _read_amplifier_header(intan_dir)
        amplifier_path = os.path.join(intan_dir, "amplifier.dat")
        channel_to_raw = read_amplifier_data_with_memmap(amplifier_path, amplifier_channels)

        # Order this file's trials by epoch start (epochs are in seconds), block by
        # `block_size` task_ids. All trials contribute to the threshold estimate;
        # only trials mapping to a stim we're parsing get written.
        trials = sorted(
            ((task_id, epoch[0], epoch[1]) for task_id, epoch in epochs_by_task.items()
             if epoch is not None),
            key=lambda t: t[1])
        if not trials:
            return []
        blocks = [trials[i:i + self.block_size]
                  for i in range(0, len(trials), self.block_size)]
        refractory_samples = max(1, int(self.refractory_sec * sample_rate))

        rows = []
        for channel, raw in channel_to_raw.items():
            cval = channel.value
            filtered = highpass_filter(np.asarray(raw, dtype=np.float64),
                                       sample_rate, self.highpass_hz)
            n = len(filtered)
            for block in blocks:
                b_start = max(0, int(block[0][1] * sample_rate))
                b_end = min(n, int(block[-1][2] * sample_rate))
                if b_end <= b_start:
                    continue
                sigma = float(np.median(np.abs(filtered[b_start:b_end]))) / 0.6745
                threshold = -self.threshold_k * sigma
                for task_id, start_s, end_s in block:
                    stim_id = task_to_stim.get(task_id)
                    if stim_id is None:
                        continue
                    s = max(0, int(start_s * sample_rate))
                    e = min(n, int(end_s * sample_rate))
                    duration = end_s - start_s
                    if e <= s or duration <= 0:
                        continue
                    count = _count_mad_negative_spikes(
                        filtered[s:e], threshold, refractory_samples)
                    rows.append((stim_id, task_id, cval, self.mua_metric,
                                 count / duration))
        return rows


def get_current_date_as_YYYY_MM_DD() -> str:
    # Get current date
    now = datetime.now()

    # Format the date as "YYYY-MM-DD"
    return now.strftime("%Y-%m-%d")


def filter_spikes_with_epochs(spike_tstamps_for_channels: dict[Channel, list[float]],
                              epochs_for_task_ids: dict[int, tuple[int, int]], task_id: int,
                              sample_rate: float = 30000) -> dict[
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
            spikes_per_second_for_channels[channel] = len(spikes) / (epoch[1] / sample_rate - epoch[0] / sample_rate)
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

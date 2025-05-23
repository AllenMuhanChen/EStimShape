#!/usr/bin/env python3
import pickle
from typing import List

import matplotlib.pyplot as plt
import pandas as pd
import xmltodict
from matplotlib.gridspec import GridSpec

from clat.compile.task.cached_task_fields import CachedTaskFieldList, CachedTaskDatabaseField
from clat.compile.task.classic_database_task_fields import StimSpecIdField, StimSpecField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.util.connection import Connection
from clat.util.time_util import When
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context


def plot_raster_by_groups(conn, task_ids):
    # Compile the data first

    data = compile_data(conn)

    # Group stimuli types
    isochromatic_types = ['Red', 'Green', 'Cyan', 'Orange']
    isoluminant_types = ['RedGreen', 'CyanOrange']

    # Create figure with two subfigures for isochromatic and isoluminant
    fig = plt.figure(figsize=(15, 10))
    gs = GridSpec(2, 1, height_ratios=[len(isochromatic_types), len(isoluminant_types)])

    # First subplot for isochromatic stimuli
    ax1 = fig.add_subplot(gs[0])
    plot_group_rasters(data, isochromatic_types, ax1, "Isochromatic Stimuli")

    # Second subplot for isoluminant stimuli
    ax2 = fig.add_subplot(gs[1])
    plot_group_rasters(data, isoluminant_types, ax2, "Isoluminant Stimuli")

    plt.tight_layout()
    return fig


def plot_group_rasters(data, types, ax, title):
    current_y = 0
    type_positions = {}

    for stim_type in types:
        type_data = data[data['Type'] == stim_type]
        frequencies = sorted(type_data['Frequency'].unique())
        freq_trial_counts = {}  # Store trial counts per frequency
        freq_y_positions = {}  # Store y-position for each frequency

        for freq in frequencies:
            freq_data = type_data[type_data['Frequency'] == freq]
            freq_trial_counts[freq] = len(freq_data)
            freq_y_positions[freq] = current_y + len(freq_data) / 2  # Middle position for this frequency

            for _, trial in freq_data.iterrows():
                spikes_by_channel = trial['Spikes by Channel']
                for channel, spike_times in spikes_by_channel.items():
                    ax.vlines(spike_times, current_y, current_y + 0.9, color='black', lw=0.5)
                current_y += 1

        if len(frequencies) > 0:
            type_positions[stim_type] = current_y - sum(freq_trial_counts.values()) / 2

            # Add frequency labels
            for freq, y_pos in freq_y_positions.items():
                ax.text(1.02, y_pos, f'{freq} Hz', transform=ax.get_yaxis_transform(),
                        verticalalignment='center', fontsize=8)

            current_y += 1  # Space between types

    ax.set_title(title)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Trials')

    # Add stimulus type labels (farther to the right to not overlap with frequency labels)
    for stim_type, pos in type_positions.items():
        ax.text(1.15, pos, stim_type, transform=ax.get_yaxis_transform(),
                verticalalignment='center', fontweight='bold')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if current_y > 0:
        ax.set_ylim(-0.5, current_y + 0.5)
        ax.set_xlim(0, 0.5)  # Adjust based on your trial duration


def compile_data(conn: Connection) -> pd.DataFrame:
    # Set up parser
    task_ids = TaskIdCollector(conn).collect_task_ids()
    parser = MultiFileParser(to_cache=True, cache_dir=context.isogabor_parsed_spikes_path)

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(TypeField(conn))
    fields.append(FrequencyField(conn))
    fields.append(SizeField(conn))
    fields.append(PhaseField(conn))
    fields.append(LocationField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))

    data = fields.to_data(task_ids)
    return data


class EpochStartStopTimesField(CachedTaskDatabaseField):
    def __init__(self, conn: Connection, parser: type(MultiFileParser), all_task_ids: list[int], intan_files_dir: str):
        super().__init__(conn)
        self.parser = parser
        self.intan_files_dir = intan_files_dir
        self.all_task_ids = all_task_ids

    def get(self, task_id: int) -> tuple:
        _, epochs_by_task_id = self.parser.parse(self.all_task_ids,
                                                 intan_files_dir=self.intan_files_dir)
        if task_id not in epochs_by_task_id:
            return None
        return epochs_by_task_id[task_id]

    def get_name(self):
        return "Epoch"


def read_pickle(path: str):
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
            if isinstance(data, dict):
                return data
            else:
                print(f"Error: The pickle file does not contain a dictionary.")
                return None
    except Exception as e:
        print(f"An error occurred while reading the pickle file: {e}")
        return None


class WindowSortSpikesByUnitField(EpochStartStopTimesField):
    def __init__(self, conn: Connection, parser: type(MultiFileParser), all_task_ids: list[int], intan_files_dir: str,
                 sort_dir: str):
        super().__init__(conn, parser, all_task_ids, intan_files_dir)
        self.sort_dir = sort_dir

    def get(self, task_id: int) -> dict:
        spike_tstamps_by_unit = {}
        _, epochs_by_task_id = self.parser.parse(self.all_task_ids,
                                                 intan_files_dir=self.intan_files_dir)
        epochs = epochs_by_task_id[task_id]

        spike_indices_by_unit_by_channel = read_pickle(self.sort_dir)
        for channel, spike_indices_by_unit in spike_indices_by_unit_by_channel.items():
            for unit_name, spike_indices in spike_indices_by_unit.items():
                new_unit_name = f"{channel}_{unit_name}"
                spikes = [spike_index / self.parser.sample_rate - epochs[0] for spike_index in spike_indices if epochs[0] <= spike_index / self.parser.sample_rate < epochs[1]]
                spike_tstamps_by_unit[new_unit_name] = spikes
        return spike_tstamps_by_unit

    def get_and_cache(self, name: str, task_id: int) -> dict:
        data = self.get(task_id)
        self._cache_value(name, task_id, data)

        # return the cached value rather than raw value to ensure same data-types are returned for all calls
        cached_value = self._get_cached_value(name, task_id)
        return self.convert_from_string(cached_value)
    def get_name(self):
        return "Window Sort Spikes By Unit"

class WindowSortSpikeRatesByUnitField(WindowSortSpikesByUnitField):
    def __init__(self, conn: Connection, parser: type(MultiFileParser), all_task_ids: list[int], intan_files_dir: str,
                 sort_dir: str):
        super().__init__(conn, parser, all_task_ids, intan_files_dir, sort_dir)

    def get(self, task_id: int) -> dict:
        spikes_by_unit = self.get_cached_super(task_id, WindowSortSpikesByUnitField, self.parser, self.all_task_ids, self.intan_files_dir, self.sort_dir)
        epoch = self.get_cached_super(task_id, EpochStartStopTimesField, self.parser, self.all_task_ids, self.intan_files_dir)

        trial_length = epoch[1] - epoch[0]
        spike_rates_by_unit = {unit_name: len(spikes) / (trial_length) for unit_name, spikes in spikes_by_unit.items()}

        return spike_rates_by_unit

    def get_and_cache(self, name: str, task_id: int) -> dict:
        data = self.get(task_id)
        self._cache_value(name, task_id, data)

        # return the cached value rather than raw value to ensure same data-types are returned for all calls
        cached_value = self._get_cached_value(name, task_id)
        return self.convert_from_string(cached_value)

    def get_name(self):
        return "Window Sort Spike Rates By Unit"

class WindowSortSpikesForUnitField(WindowSortSpikesByUnitField):
    def __init__(self, conn: Connection, parser: type(MultiFileParser), all_task_ids: list[int], intan_files_dir: str,
                 sort_dir: str, unit_name: str):
        super().__init__(conn, parser, all_task_ids, intan_files_dir, sort_dir)
        self.unit_name = unit_name

    def get(self, task_id: int) -> dict:
        spikes_by_unit = self.get_cached_super(task_id, WindowSortSpikesByUnitField, self.parser, self.all_task_ids, self.intan_files_dir, self.sort_dir)

        return spikes_by_unit.get(self.unit_name, [])

    def get_and_cache(self, name: str, task_id: int) -> dict:
        data = self.get(task_id)
        self._cache_value(name, task_id, data)
        return data
    def get_name(self):
        return "Window Sort Unit"



class IntanSpikesByChannelField(CachedTaskDatabaseField):
    """
    Retrieves spike timestamps by channel from Intan files for a given task ID
    and makes them relative to the start of the epoch

    Retrieves the spikes that Intan software detects, saved in spike.dat files
    """

    def __init__(self, conn: Connection, parser: type(MultiFileParser), all_task_ids: list[int], intan_files_dir: str):
        super().__init__(conn)
        self.parser = parser
        self.intan_files_dir = intan_files_dir
        self.all_task_ids = all_task_ids

    def get(self, task_id) -> dict:
        spikes_by_channel_by_task_id, epochs_by_task_id = self.parser.parse(self.all_task_ids,
                                                                            intan_files_dir=self.intan_files_dir)
        if task_id not in spikes_by_channel_by_task_id.keys():
            raise ValueError(f"Task ID {task_id} not found in spikes_by_channel_by_task_id")
        spikes_by_channel = spikes_by_channel_by_task_id[task_id]
        if task_id not in epochs_by_task_id.keys():
            raise ValueError(f"Task ID {task_id} not found in epochs_by_task_id")
        epoch_start = epochs_by_task_id[task_id][0]
        # convert timestamp to epoch_start relative
        spikes_by_channel = {channel.value: [spike - epoch_start for spike in spikes] for channel, spikes in
                             spikes_by_channel.items()}

        # Convert Channel enum keys to strings to prevent serialization issues
        return spikes_by_channel

    def get_name(self):
        return "Spikes by channel"


class IntanSpikeRateByChannelField(CachedTaskDatabaseField):
    def __init__(self, conn: Connection, parser: type(MultiFileParser), all_task_ids: list[int], intan_files_dir: str):
        super().__init__(conn)
        self.parser = parser
        self.intan_files_dir = intan_files_dir
        self.all_task_ids = all_task_ids

    def get(self, task_id) -> dict:
        spikes_by_channel_by_task_id, epochs_by_task_id = self.parser.parse(self.all_task_ids, self.intan_files_dir)
        spikes_by_channels = spikes_by_channel_by_task_id[task_id]
        epoch = epochs_by_task_id[task_id]

        spike_rate_by_channel = {}
        for channel, spike_times in spikes_by_channels.items():
            print(f"Processing task {task_id} on channel {channel.value}")
            spike_count = len([time for time in spike_times if epoch[0] <= time <= epoch[1]])
            spike_rate = spike_count / (epoch[1] - epoch[0])
            spike_rate_by_channel[channel.value] = spike_rate

        return spike_rate_by_channel

    def get_name(self):
        return "Spike Rate by channel"


class TypeField(StimSpecField):
    def get(self, task_id) -> str:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_spec_type = stim_spec_dict['StimSpec']['type']
        return stim_spec_type

    def get_name(self):
        return "Type"

class IsoTypeField(TypeField):
    def get(self, task_id) -> str:
        type = self.get_cached_super(task_id, TypeField)
        if type in ["Red", "Green", "Cyan", "Orange"]:
            return "Isochromatic"
        elif type in ["RedGreen", "CyanOrange"]:
            return "Isoluminant"
        else:
            return None

    def get_name(self):
        return "IsoType"


class OrientationField(StimSpecField):
    def get(self, task_id) -> str:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_spec_type = stim_spec_dict['StimSpec']['orientation']
        return stim_spec_type

    def get_name(self):
        return "Orientation"


class SizeField(StimSpecField):
    def get(self, task_id) -> str:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_spec_type = stim_spec_dict['StimSpec']['size']
        return stim_spec_type

    def get_name(self):
        return "Size"


class LocationField(StimSpecField):
    def get(self, task_id) -> tuple[float, float]:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        x = stim_spec_dict['StimSpec']['xCenter']
        y = stim_spec_dict['StimSpec']['yCenter']
        return x, y

    def get_name(self):
        return "Location"


class FrequencyField(StimSpecField):
    def get(self, task_id) -> float:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        frequency = stim_spec_dict['StimSpec']['frequency']
        return float(frequency)

    def get_name(self):
        return "Frequency"


class MixedFrequencyField(StimSpecField):
    def get(self, task_id) -> list[float] | None:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_type = stim_spec_dict['StimSpec']['type']
        if 'Mixed' not in stim_type:
            return None
        chromatic_frequency = stim_spec_dict['StimSpec']['chromaticSpec']['frequency']
        luminance_frequency = stim_spec_dict['StimSpec']['luminanceSpec']['frequency']
        return f"{chromatic_frequency}, {luminance_frequency}"

    def get_name(self):
        return "Mixed Frequency"

class MixedPhaseField(StimSpecField):
    def get(self, task_id) -> list[float] | None:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_type = stim_spec_dict['StimSpec']['type']
        if "Mixed" not in stim_type:
            return None
        chromatic_phase = stim_spec_dict['StimSpec']['chromaticSpec']['phase']
        luminance_phase = stim_spec_dict['StimSpec']['luminanceSpec']['phase']
        return f"{chromatic_phase}, {luminance_phase}"

    def get_name(self):
        return "Mixed Phase"

class AlignedPhaseField(MixedPhaseField):
    def get(self, task_id) -> str | None:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_type = stim_spec_dict['StimSpec']['type']
        if "Mixed" not in stim_type:
            return None
        chromatic_phase = stim_spec_dict['StimSpec']['chromaticSpec']['phase']
        luminance_phase = stim_spec_dict['StimSpec']['luminanceSpec']['phase']
        if chromatic_phase == luminance_phase:
            return "Aligned Phase"
        else:
            return "Misaligned Phase"

    def get_name(self):
        return "Aligned Phase"

class AlignedFrequencyField(MixedFrequencyField):
    def get(self, task_id) -> str | None:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_type = stim_spec_dict['StimSpec']['type']
        if "Mixed" not in stim_type:
            return None
        chromatic_frequency = stim_spec_dict['StimSpec']['chromaticSpec']['frequency']
        luminance_frequency = stim_spec_dict['StimSpec']['luminanceSpec']['frequency']
        if chromatic_frequency == luminance_frequency:
            return "Aligned Frequency"
        else:
            return "Misaligned Frequency"

    def get_name(self):
        return "Aligned Frequency"
class PhaseField(StimSpecField):
    def get(self, task_id) -> float:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        phase = stim_spec_dict['StimSpec']['phase']
        return phase

    def get_name(self):
        return "phase"


def main():
    date = '2025-04-03'
    conn = Connection(context.isogabor_database)
    task_collector = TaskIdCollector(conn)
    task_ids = task_collector.collect_task_ids()

    # Create raster plots
    fig = plot_raster_by_groups(conn, task_ids)
    plt.show()


if __name__ == "__main__":
    main()

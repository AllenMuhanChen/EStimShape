#!/usr/bin/env python3

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
        spikes_by_channel = spikes_by_channel_by_task_id[task_id]
        epoch_start = epochs_by_task_id[task_id][0]
        # convert timestamp to epoch_start relative
        spikes_by_channel = {channel.value: [spike - epoch_start for spike in spikes] for channel, spikes in
                             spikes_by_channel.items()}

        # Convert Channel enum keys to strings to prevent serialization issues
        return spikes_by_channel

    def get_name(self):
        return "Spikes by Channel"


class SpikeRateByChannelField(CachedTaskDatabaseField):
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
        return "Spike Rate by Channel"


class TypeField(StimSpecField):
    def get(self, task_id) -> str:
        stim_spec = self.get_cached_super(task_id, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_spec_type = stim_spec_dict['StimSpec']['type']
        return stim_spec_type

    def get_name(self):
        return "Type"


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
        return frequency

    def get_name(self):
        return "Frequency"


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

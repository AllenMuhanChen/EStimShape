import pandas as pd
import xmltodict

from clat.compile.task.compile_task_id import TaskIdCollector
from clat.compile.trial.cached_fields import CachedFieldList
from clat.compile.trial.trial_collector import TrialCollector
from clat.util.connection import Connection
from clat.util.time_util import When
from src.analysis.cached_fields import TaskIdField, StimIdField, StimSpecField
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context


def main():
    date = '2025-02-17'
    conn = Connection(context.isogabor_database)
    trial_collector = TrialCollector(conn)
    task_ids = trial_collector.collect_trials()
    data = compile_data(conn, task_ids, date)

    # remove NaN
    data = data.dropna()
    print(data.to_string())


def compile_data(conn: Connection, trial_tstamps: list[When], date) -> pd.DataFrame:
    # set up way to parse here? We may need to parse multiple files?
    task_ids = TaskIdCollector(conn).collect_task_ids()

    parser = MultiFileParser()
    spikes_by_channel_by_task_id, epochs_by_task_id = parser.parse(task_ids,
                                                                   intan_files_dir=context.isogabor_intan_path + '/' + date)

    fields = CachedFieldList()
    fields.append(TaskIdField(conn))
    fields.append(StimIdField(conn))
    fields.append(TypeField(conn))
    fields.append(OrientationField(conn))
    fields.append(SizeField(conn))
    fields.append(LocationField(conn))
    # fields.append(SpikesByChannelField(conn, spikes_by_channel_by_task_id))
    fields.append(SpikeRateByChannelField(conn, spikes_by_channel_by_task_id, epochs_by_task_id))
    data = fields.to_data(trial_tstamps)

    return data


class SpikesByChannelField(TaskIdField):
    def __init__(self, conn: Connection, spikes_by_channel_by_task_id: dict):
        super().__init__(conn)
        self.spikes_by_channel_by_task_id = spikes_by_channel_by_task_id

    def get(self, when: When) -> dict:
        task_id = self.get_cached_super(when, TaskIdField)
        return self.spikes_by_channel_by_task_id[task_id]

    def get_name(self):
        return "Spikes by Channel"


class SpikeRateByChannelField(SpikesByChannelField):
    def __init__(self, conn: Connection, spikes_by_channel_by_task_id: dict, epochs_by_task_id):
        super().__init__(conn, spikes_by_channel_by_task_id)
        self.epochs_by_task_id = epochs_by_task_id

    def get(self, when: When) -> dict:
        task_id = self.get_cached_super(when, TaskIdField)
        spikes_for_channels = self.spikes_by_channel_by_task_id[task_id]
        epoch = self.epochs_by_task_id[task_id]

        spike_rate_by_channel = {}
        for channel, spike_times in spikes_for_channels.items():
            print(f"Processing task {task_id} on channel {channel.value}")
            spike_count = len([time for time in spike_times if epoch[0] <= time <= epoch[1]])
            spike_rate = spike_count / (epoch[1] - epoch[0])
            spike_rate_by_channel[channel] = spike_rate

        return spike_rate_by_channel

    def get_name(self):
        return "Spike Rate by Channel"


class TypeField(StimSpecField):
    def get(self, when: When) -> str:
        stim_spec = self.get_cached_super(when, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_spec_type = stim_spec_dict['StimSpec']['type']
        return stim_spec_type

    def get_name(self):
        return "Type"


class OrientationField(StimSpecField):
    def get(self, when: When) -> str:
        stim_spec = self.get_cached_super(when, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_spec_type = stim_spec_dict['StimSpec']['orientation']
        return stim_spec_type

    def get_name(self):
        return "Orientation"


class SizeField(StimSpecField):
    def get(self, when: When) -> str:
        stim_spec = self.get_cached_super(when, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        stim_spec_type = stim_spec_dict['StimSpec']['size']
        return stim_spec_type

    def get_name(self):
        return "Size"


class LocationField(StimSpecField):
    def get(self, when: When) -> tuple[float, float]:
        stim_spec = self.get_cached_super(when, StimSpecField)
        stim_spec_dict = xmltodict.parse(stim_spec)

        x = stim_spec_dict['StimSpec']['xCenter']
        y = stim_spec_dict['StimSpec']['yCenter']
        return x, y

    def get_name(self):
        return "Location"


if __name__ == "__main__":
    main()

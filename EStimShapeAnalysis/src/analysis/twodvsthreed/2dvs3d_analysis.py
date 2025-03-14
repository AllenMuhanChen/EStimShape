from typing import Callable

import numpy as np

from clat.compile.task.compile_task_id import TaskIdCollector
from clat.compile.tstamp.cached_tstamp_fields import CachedFieldList
from clat.compile.tstamp.trial_tstamp_collector import TrialCollector
from clat.compile.tstamp.classic_database_tstamp_fields import TaskIdField, StimIdField
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When
from src.analysis.isogabor.isogabor_analysis import IntanSpikesByChannelField, SpikeRateByChannelField
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context


def main():
    date = '2025-02-19'
    conn = Connection(context.twodvsthreed_database)
    trial_tstamps = TrialCollector(conn, time_util.on_date(2025, 2, 19)).collect_trials()
    task_ids = TaskIdCollector(conn).collect_task_ids()

    parser = MultiFileParser(to_cache=True, cache_dir=context.twodvsthreed_parsed_spikes_path)
    intan_files_dir = context.twodvsthreed_intan_path + '/' + date

    spikes_by_channel_by_task_id = {}
    epochs_by_task_id = {}

    fields = CachedFieldList()
    fields.append(TaskIdField(conn))
    fields.append(StimIdField(conn))
    fields.append(TextureField(conn))
    fields.append(ColorField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, intan_files_dir)),
    fields.append(SpikeRateByChannelField(conn, parser, task_ids, intan_files_dir)),
    fields.append(GAClusterResponseField(conn, parser, task_ids, intan_files_dir, np.sum))
    data = fields.to_data(trial_tstamps)

    print(data.to_string())


class TextureField(StimIdField):

    def get(self, when: When) -> dict:
        id = self.get_cached_super(when, StimIdField)
        self.conn.execute("SELECT texture_type FROM StimTexture WHERE stim_id = %s",
                          params=(id,))
        texture = self.conn.fetch_one()
        return texture

    def get_name(self):
        return "Texture"


class ColorField(StimIdField):

    def get(self, when: When) -> dict:
        id = self.get_cached_super(when, StimIdField)
        self.conn.execute("SELECT red, green, blue FROM StimColor WHERE stim_id = %s",
                          params=(id,))
        color = self.conn.fetch_all()
        return color[0]

    def get_name(self):
        return "RGB"


class GAClusterResponseField(SpikeRateByChannelField):
    def __init__(self, conn: Connection, parser: MultiFileParser, all_task_ids: list[int], intan_files_dir: str,
                 cluster_combination_method: Callable[[list[float]], float]):
        super().__init__(conn, parser, all_task_ids, intan_files_dir)
        self.cluster_combination_method = cluster_combination_method

    def get(self, when: When) -> float:
        spike_rate_by_channel = self.get_cached_super(when, SpikeRateByChannelField, self.parser, self.all_task_ids,
                                                      self.intan_files_dir)

        channels = self._fetch_cluster_channels()

        # get response per channel in the cluster
        cluster_response_vector = []
        for channel in channels:
            cluster_response_vector.append(spike_rate_by_channel[channel])

        return self.cluster_combination_method(cluster_response_vector)

    def _fetch_cluster_channels(self):
        self.conn.execute("SELECT channel FROM ClusterInfo ORDER BY experiment_id DESC, gen_id")
        channels = self.conn.fetch_all()
        # remove duplicate channels
        channels = list(dict.fromkeys(channels))
        # unpack tuples
        channels = [channel[0] for channel in channels]
        return channels

    def get_name(self):
        return "Cluster Response"


if __name__ == "__main__":
    main()

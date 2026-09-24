import numpy as np
import pandas as pd

from clat.intan.channels import Channel
from clat.util.connection import Connection
from src.cluster.cluster_app import ClusterApplicationWindow
from src.cluster.cluster_app_classes import DataLoader, DataExporter, ClusterLoader
from src.cluster.dimensionality_reduction import PCAReducer, MDSReducer, TSNEReducer, KernelPCAReducer, \
    SparsePCAReducer
from src.cluster.mock_cluster_app import get_qapplication_instance
from src.cluster.probe_mapping import DBCChannelMapper
from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.pga.mua_channel_responses import MuaChannelResponseStore
from src.startup import context


def channels_for_prefix(prefix: str):
    '''
    Returns a list of channels with names starting with the given prefix
    '''
    return [channel for channel in Channel if channel.name.startswith(prefix)]


class DbDataLoader(DataLoader):
    """Loads per-channel response vectors from MUAChannelResponses (the wideband
    -kxMAD detector's output) rather than the spike.dat ChannelResponses table.

    Defaults to the current GA experiment's store (the metric the live GA writes);
    if the table is still empty it is backfilled on first load.
    """

    def __init__(self, store: MuaChannelResponseStore | None = None):
        self.store = store if store is not None else MuaChannelResponseStore.for_ga()
        self.conn = self.store.conn
        self.mua_metric = self.store.mua_metric

    def load_data_for_channels(self, max_gen: int | None = None):
        # The data will be dictionary between channels and their data
        # the data will be an (n_tasks) ndarray of the response rates
        self.store.ensure_populated()
        data_for_channels = {}
        for index, channel in enumerate(channels_for_prefix("A")):
            data_for_channels[channel] = self.get_spikes_per_channel(channel.value, max_gen)
        return data_for_channels

    def get_max_generation(self) -> int:
        """Highest generation id with MUA responses recorded (1 if none)."""
        self.store.ensure_populated()
        return self.store.max_gen()

    def get_spikes_per_channel(self, channel_name: str, max_gen: int | None = None) -> np.ndarray:
        """Average spikes/s per stim for one channel (averaged across its tasks),
        ordered by stim_id; optionally only stims from generations <= max_gen."""
        return self.store.avg_rate_by_stim(channel_name, max_gen)


class DbClusterLoader(ClusterLoader):
    def __init__(self, multi_ga_db_util: MultiGaDbUtil):
        self.db_util = multi_ga_db_util

    def load_current_cluster_info(self):
        try:
            return self.db_util.read_current_cluster_with_gen_id(context.ga_name)
        except Exception:
            return None


class DbDataExporter(DataExporter):
    def __init__(self, multi_ga_db_util: MultiGaDbUtil):
        self.db_util = multi_ga_db_util

    def export_channels_for_clusters(self, channels_for_clusters: dict[int, list[Channel]]):
        cluster_to_export = 1
        channels_to_export = channels_for_clusters[cluster_to_export]
        print(f"Exporting channels for cluster {cluster_to_export}: {channels_to_export}")

        current_experiment_id = self.db_util.read_current_experiment_id(context.ga_name)
        current_gen_id = self.db_util.read_ready_gas_and_generations_info().get(context.ga_name)

        print(f"Current experiment id: {current_experiment_id}")
        print(f"Current generation id: {current_gen_id}")

        for channel in channels_to_export:
            self.db_util.write_cluster_info(current_experiment_id, current_gen_id, channel.value)


def main():

    app = get_qapplication_instance()
    window = ClusterApplicationWindow(DbDataLoader(),
                                      DbDataExporter(context.ga_config.db_util),
                                      [PCAReducer(),
                                       MDSReducer(),
                                       KernelPCAReducer(),
                                       SparsePCAReducer()],
                                      DBCChannelMapper("A"),
                                      DbClusterLoader(context.ga_config.db_util))

    #choosing the dimensionality reduction method
    #MDS: Multidimensional Scaling, a method that projects the data into a lower dimensional space while preserving the distances between the data points
    #    this is useful when we want to visualize the data in a lower dimensional space, while preserving the similarity relationships between the data.
    #SparsePCA: Sparse Principal Component Analysis, a variant of PCA that introduces sparsity in the loadings matrix
    #    this is useful when we want to make interpreting the PC's easier, as it enforces that each PC is a linear combination of only a few stimuli.
    #    this is particularily useful when we expect few stimuli to be relevant to the neural response.
    #KernelPCA: Kernel Principal Component Analysis, a variant of PCA that uses a kernel function to project the data into a higher dimensional space
    #    this is useful when the data is not linearly separable in the original space, but is in a higher dimensional space.

    window.show()
    app.exec_()


if __name__ == '__main__':
    main()

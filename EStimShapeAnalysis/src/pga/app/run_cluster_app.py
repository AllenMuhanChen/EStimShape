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
from src.startup import context


# Detection method the cluster app reads from MUAChannelResponses. Matches the
# GA MUA pipeline default (-4x MAD, threshold refreshed every 100 task_ids).
DEFAULT_MUA_METRIC = "mad_k4_block100"


def channels_for_prefix(prefix: str):
    '''
    Returns a list of channels with names starting with the given prefix
    '''
    return [channel for channel in Channel if channel.name.startswith(prefix)]


class DbDataLoader(DataLoader):
    """Loads per-channel response vectors from MUAChannelResponses (the wideband
    -kxMAD detector's output) rather than the spike.dat ChannelResponses table."""

    def __init__(self, conn: Connection, mua_metric: str = DEFAULT_MUA_METRIC):
        self.conn = conn
        self.mua_metric = mua_metric

    def load_data_for_channels(self, max_gen: int | None = None):
        # The data will be dictionary between channels and their data
        # the data will be an (n_tasks) ndarray of the response rates
        data_for_channels = {}
        for index, channel in enumerate(channels_for_prefix("A")):
            spikes_data = self.get_spikes_per_channel(channel.value, max_gen)
            # if spikes_data.size == 0:
            #     continue
            data_for_channels[channel] = spikes_data
        return data_for_channels

    def get_max_generation(self) -> int:
        """
        Returns the highest generation id that currently has channel responses recorded.
        Falls back to 1 when no generation information is available.
        """
        query = """
            SELECT MAX(sgi.gen_id)
            FROM StimGaInfo sgi
            JOIN MUAChannelResponses cr ON cr.stim_id = sgi.stim_id
            WHERE cr.mua_metric = %s
        """
        self.conn.execute(query, (self.mua_metric,))
        max_gen = self.conn.fetch_one()
        if max_gen is None:
            return 1
        return int(max_gen)

    def get_spikes_per_channel(self, channel_name: str, max_gen: int | None = None) -> np.ndarray:
        """
        Fetches average spikes per second for a specific channel, grouped by stim_id and averaged across task_ids,
        ordered by stim_id, and returns as a numpy array.

        Parameters:
        - channel_name: The name of the channel for which average spikes per second are required.
        - max_gen: If provided, only include responses to stimuli from generations up to and
          including this generation. If None, include all responses.

        Returns:
        - A numpy array containing the averaged spikes_per_second for the specified channel,
          grouped by stim_id and ordered by stim_id.
        """
        if max_gen is None:
            query = """
                SELECT stim_id, AVG(spikes_per_second) as avg_spikes_per_second
                FROM MUAChannelResponses
                WHERE channel = %s AND mua_metric = %s
                GROUP BY stim_id
                ORDER BY stim_id
            """
            params = (str(channel_name), self.mua_metric)
        else:
            query = """
                SELECT cr.stim_id, AVG(cr.spikes_per_second) as avg_spikes_per_second
                FROM MUAChannelResponses cr
                JOIN StimGaInfo sgi ON cr.stim_id = sgi.stim_id
                WHERE cr.channel = %s AND cr.mua_metric = %s AND sgi.gen_id <= %s
                GROUP BY cr.stim_id
                ORDER BY cr.stim_id
            """
            params = (str(channel_name), self.mua_metric, max_gen)
        self.conn.execute(query, params)  # Execute the query with the parameter
        data = self.conn.fetch_all()  # Fetch all results

        # If no data is returned, return an empty array
        if not data:
            return np.array([])

        # Convert list of tuples into a numpy array, extracting only the averaged spikes_per_second
        spikes_array = np.array([float(entry[1]) for entry in data])
        return spikes_array


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
    window = ClusterApplicationWindow(DbDataLoader(context.ga_config.connection()),
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

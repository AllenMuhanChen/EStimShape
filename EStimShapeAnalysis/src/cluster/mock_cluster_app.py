import sys

import numpy as np
from PyQt5.QtWidgets import QApplication
from sklearn.datasets import make_blobs, make_sparse_uncorrelated, make_classification

from clat.intan.channels import Channel
from src.cluster.cluster_app import ClusterApplicationWindow
from src.cluster.cluster_app_classes import DataLoader, DataExporter, ChannelMapper
from src.cluster.dimensionality_reduction import PCAReducer, MDSReducer, TSNEReducer, KernelPCAReducer, \
    SparsePCAReducer
from src.cluster.probe_mapping import DBCChannelMapper


class MockDataLoader(DataLoader):
    def __init__(self, channel_mapper: DBCChannelMapper):
        self.channel_mapper = channel_mapper
    def load_data_for_channels(self):
        # Replace this with your actual mock data
        X, _ = make_blobs(n_samples=len(self.channel_mapper.channels_top_to_bottom), centers=8, n_features=100, random_state=42, shuffle=False)
        # X, _ = make_classification(n_samples=len(self.channels_for_prefix("A")), n_features=100, n_informative=20, n_classes=3, n_clusters_per_class=1)

        # Assign each data point to a channel from A_000 to A_031
        data_for_channels = {}
        for index, channel in enumerate(self.channel_mapper.channels_top_to_bottom):
            data_for_channels[channel] = X[index]
        return data_for_channels

    def channels_for_prefix(cls, prefix: str):
        return [channel for channel in Channel if channel.name.startswith(prefix)]


class MockDataExporter(DataExporter):
    def export_channels_for_clusters(self, channels_for_clusters: dict[int, list[Channel]]):
        print(channels_for_clusters[1])




def get_qapplication_instance():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


if __name__ == '__main__':
    app = get_qapplication_instance()
    mapper = DBCChannelMapper("A")
    window = ClusterApplicationWindow(MockDataLoader(mapper),
                                      MockDataExporter(),
                                      [PCAReducer(),
                                       MDSReducer(),
                                       TSNEReducer(),
                                       KernelPCAReducer(),
                                       SparsePCAReducer()],
                                      mapper)
    window.show()
    app.exec_()

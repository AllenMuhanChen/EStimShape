import sys

import numpy as np
from PyQt5.QtWidgets import QApplication
from sklearn.datasets import make_blobs, make_sparse_uncorrelated, make_classification

from clat.intan.channels import Channel
from newga.gui.cluster.cluster_app import ClusterApplicationWindow
from newga.gui.cluster.cluster_app_classes import DataLoader, DataExporter, ChannelMapper
from newga.gui.cluster.dimensionality_reduction import PCAReducer, MDSReducer, TSNEReducer, KernelPCAReducer, \
    SparsePCAReducer
from newga.gui.cluster.probe_mapping import DBCChannelMapper


class MockDataLoader(DataLoader):
    def load_data_for_channels(self):
        # Replace this with your actual mock data
        X, _ = make_blobs(n_samples=len(self.channels_for_prefix("A")), centers=3, n_features=100, random_state=42, shuffle=False)
        # X, _ = make_classification(n_samples=len(self.channels_for_prefix("A")), n_features=100, n_informative=20, n_classes=3, n_clusters_per_class=1)

        # Assign each data point to a channel from A_000 to A_031
        data_for_channels = {}
        for index, channel in enumerate(self.channels_for_prefix("A")):
            data_for_channels[channel] = X[index]
        return data_for_channels

    def channels_for_prefix(cls, prefix: str):
        return [channel for channel in Channel if channel.name.startswith(prefix)]


class MockDataExporter(DataExporter):
    def export_channels_for_clusters(self, channels_for_clusters: dict[int, list[Channel]]):
        print(channels_for_clusters[1])


class MockChannelMapper(ChannelMapper):
    def __init__(self, channels):
        # Initialize the dictionary mapping channels to coordinates
        self.channel_map = {}
        for channel in channels:
            prefix = channel.name[0]  # Get the first letter (A, B, C, or D)
            index = int(channel.name.split('_')[1])  # Get the index after the underscore
            x = ['A', 'B', 'C', 'D'].index(prefix) * 4 + index // 16  # x coordinate based on the letter and index
            y = index % 16  # y coordinate based on the index
            self.channel_map[channel] = np.array([x, y])

    def get_coordinates(self, channel):
        # Return the coordinates for a given channel
        return self.channel_map.get(channel, None)


def get_qapplication_instance():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


if __name__ == '__main__':
    app = get_qapplication_instance()
    window = ClusterApplicationWindow(MockDataLoader(),
                                      MockDataExporter(),
                                      [PCAReducer(),
                                       MDSReducer(),
                                       TSNEReducer(),
                                       KernelPCAReducer(),
                                       SparsePCAReducer()],
                                      DBCChannelMapper("A"))
    window.show()
    app.exec_()
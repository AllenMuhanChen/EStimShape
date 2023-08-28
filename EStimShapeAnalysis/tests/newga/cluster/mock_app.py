import sys

import numpy as np
from PyQt5.QtWidgets import QApplication
from sklearn.datasets import make_blobs

from intan.channels import Channel
from newga.gui.cluster.cluster_app import ClusterApplicationWindow
from newga.gui.cluster.cluster_app_classes import DataLoader, DataExporter, ChannelMapper
from newga.gui.cluster.dimensionality_reduction import PCAReducer, MDSReducer


class MockDataLoader(DataLoader):
    def load_data_for_channels(self):
        # Replace this with your actual mock data
        X, _ = make_blobs(n_samples=len(Channel), centers=3, n_features=100, random_state=42, shuffle=False)

        # Assign each data point to a channel from A_000 to A_031
        data_for_channels = {}
        for index, channel in enumerate(Channel):
            data_for_channels[channel] = X[index]
        return data_for_channels


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
    window = ClusterApplicationWindow(MockDataLoader(), MockDataExporter(), [PCAReducer(), MDSReducer()],
                                      MockChannelMapper(Channel))
    window.show()
    app.exec_()

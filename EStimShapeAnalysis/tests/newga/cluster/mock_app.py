import sys

from PyQt5.QtWidgets import QApplication
from sklearn.datasets import make_blobs

from intan.channels import Channel
from newga.cluster.app import ApplicationWindow
from newga.cluster.dimensionality_reduction import PCAReducer, MDSReducer
import os
os.environ.update({"QT_QPA_PLATFORM_PLUGIN_PATH": "/home/r2_allen/anaconda3/envs/3.11/lib/python3.11/site-packages/PyQt5/Qt5/plugins/platforms"})

class MockDataLoader:
    def load_data(self):
        # Replace this with your actual mock data
        X, _ = make_blobs(n_samples=len(Channel), centers=3, n_features=3, random_state=42, shuffle=False)

        # Assign each data point to a channel from A_000 to A_031
        data_for_channels = {}
        for index, channel in enumerate(Channel):
            data_for_channels[channel] = X[index]
        return data_for_channels
        #
        # data_for_channels = {}
        # for i in range(32):
        #     data_for_channels[Channel.A_000] = X[:, i]


class MockDataExporter:
    def export_data(self, channels_for_clusters: dict[int, list[Channel]]):
        print(channels_for_clusters[1])

def get_qapplication_instance():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


if __name__ == '__main__':
    app = get_qapplication_instance()
    window = ApplicationWindow(MockDataLoader(), MockDataExporter(), [PCAReducer(), MDSReducer()])
    window.show()
    app.exec_()


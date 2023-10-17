from typing import Protocol, Any

import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtGui import QColor
from matplotlib import cm
from matplotlib.path import Path

from clat.intan.channels import Channel

MAX_GROUPS = 10


class DataLoader(Protocol):
    def load_data_for_channels(self) -> dict[Channel, np.ndarray]:
        pass


class DataExporter(Protocol):
    def export_channels_for_clusters(self, channels_for_clusters: dict[int, list[Channel]]):
        pass


class ChannelMapper(Protocol):
    def get_coordinates(self, channel):
        pass


class ClusterManager:
    def __init__(self, channels: list[Channel]):
        self.channels = channels

        self.num_clusters = 2
        self.clusters_for_channels: dict[Channel, int] = {}
        self.color_map = cm.get_cmap('tab10', MAX_GROUPS)

    def init_clusters_for_channels(self):
        self.clusters_for_channels = {channel: 0 for channel in self.channels}
        return self.clusters_for_channels

    def remove_channels_from_cluster(self, channels, cluster):
        for channel in channels:
            if self.clusters_for_channels[channel] == cluster:
                self.clusters_for_channels[channel] = 0
        return self.clusters_for_channels

    def add_channels_to_cluster(self, channels, cluster):
        for channel in channels:
            self.clusters_for_channels[channel] = cluster
        return self.clusters_for_channels

    def delete_cluster(self, cluster) -> dict[Channel, int]:
        self.clusters_for_channels[self.clusters_for_channels == cluster] = 0
        self.num_clusters -= 1

        # Assign all current channels in that cluster to group 0
        for channel in self.clusters_for_channels.keys():
            if self.clusters_for_channels[channel] == cluster:
                self.clusters_for_channels[channel] = 0

        # Decrement the group numbers of all higher-numbered groups
        for i in range(cluster + 1, self.num_clusters + 1):
            for channel in self.channels:
                if self.clusters_for_channels[channel] == i:
                    self.clusters_for_channels[channel] = i - 1
        return self.clusters_for_channels

    def add_cluster(self):
        self.num_clusters += 1

    def get_colormap_colors_per_channel_based_on_cluster(self) -> \
            list[float]:
        cmap_color_per_channel = []
        for channel in self.channels:
            assigned_cluster_for_current_channel = self.clusters_for_channels[channel]
            cmap_color_per_channel.append(self.get_cmap_color_for_cluster(assigned_cluster_for_current_channel))
        return cmap_color_per_channel

    def get_cmap_color_for_cluster(self, i) -> float:
        color = self.color_map(i / MAX_GROUPS)  # Calculate the color of this group
        return color

    def get_qcolor_for_cluster(self, i) -> QColor:
        color = self.get_cmap_color_for_cluster(i)
        color = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))  # Convert to QColor
        return color


class Annotator:
    def __init__(self):
        pass

    @staticmethod
    def init_annotations(ax: plt.Axes) -> plt.Annotation:
        annotation = ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                 textcoords="offset points",
                                 bbox=dict(boxstyle="round", fc="w"),
                                 arrowprops=dict(arrowstyle="->"))
        annotation.set_visible(False)
        return annotation

    @staticmethod
    def show_annotation_at(x, y, text, annotated_axes: plt.Annotation) -> None:
        """

        :param x: location on axes
        :param y: location on axes
        :param text: label for annotation
        :param annotated_axes: an axes object that has been annotated with ax.annotate. Get this from init_annotations
        """
        annotated_axes.xy = (x, y)
        annotated_axes.set_text(text)
        annotated_axes.set_visible(True)

    @staticmethod
    def hide_annotations_for(annotation: plt.Annotation):
        annotation.set_visible(False)



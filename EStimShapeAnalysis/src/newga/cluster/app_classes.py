import numpy as np
from PyQt5.QtGui import QColor
from matplotlib import cm
from matplotlib.path import Path

from intan.channels import Channel

MAX_GROUPS = 10


class ClusterManager:
    def __init__(self, channels: list[Channel]):
        self.channels = channels

        self.num_clusters = 2
        self.clusters_for_channels: dict[Channel, int] = {}
        self.color_map = cm.get_cmap('tab10', MAX_GROUPS)

    def init_clusters_for_channels_from(self):
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
        for i in range(cluster + 1, self.num_clusters+1):
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

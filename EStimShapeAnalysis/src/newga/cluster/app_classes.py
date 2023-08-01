import numpy as np
from PyQt5.QtGui import QColor
from matplotlib import cm
from matplotlib.path import Path

from intan.channels import Channel

MAX_GROUPS = 10


class ClusterManager:
    def __init__(self):
        self.reduced_points_for_reducer = {}
        self.clusters_for_channels: dict[Channel, list[int]] = {}
        self.color_map = cm.get_cmap('tab10', MAX_GROUPS)

    def reduce_data(self, reducers, point_to_reduce_for_channels: dict[Channel, list[np.ndarray]]):
        ndim_points = list(point_to_reduce_for_channels.values())
        # Concatenate all the data into a single 2D array
        stacked_points = np.vstack(ndim_points)
        for reducer in reducers:
            # Perform dimensionality reduction on all data
            all_reduced_data = reducer.fit_transform(stacked_points)

            # Split the reduced data back up into channels
            reduced_data_for_channels = {}
            start_index = 0
            for channel_index, channel in enumerate(point_to_reduce_for_channels.keys()):
                # Extract the part of all_reduced_data that corresponds to this channel
                reduced_data = all_reduced_data[channel_index, :]
                reduced_data_for_channels[channel] = reduced_data

            self.reduced_points_for_reducer[reducer] = reduced_data_for_channels
        return self.reduced_points_for_reducer

    def init_clusters_for_channels(self, reducer, high_dim_points_for_channels, current_reducer) -> None:
        # Reset groups if the reducer has changed
        if current_reducer != reducer:
            self.clusters_for_channels = None
            self.current_cluster = 1
        if self.clusters_for_channels is None:
            # Initialize the groups array the first time plot() is called
            self.clusters_for_channels = {channel: 0 for channel in high_dim_points_for_channels.keys()}

    def lasso_select(self, verts, current_cluster, lasso, reduced_points_for_reducer, current_reducer):
        path = Path(verts)
        selected_channels = []

        for channel, data in reduced_points_for_reducer[current_reducer].items():
            point = data  # since each channel corresponds to one point
            if path.contains_point(point):
                selected_channels.append(channel)

        # Check the mouse button used for lasso selection
        if lasso.button == 1:  # Left-click
            # Add selected points to the current group
            for channel in selected_channels:
                self.clusters_for_channels[channel] = current_cluster
        elif lasso.button == 3:  # Right-click
            # Remove selected points from the current group
            for channel in selected_channels:
                if self.clusters_for_channels[channel] == current_cluster:
                    self.clusters_for_channels[channel] = 0
        return self.clusters_for_channels

    def assign_cmap_colors_to_channels_based_on_cluster(self, reduced_point_for_channels, clusters_for_channels) -> \
    list[float]:
        cmap_color_per_channel = []
        for channel, data in reduced_point_for_channels.items():
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

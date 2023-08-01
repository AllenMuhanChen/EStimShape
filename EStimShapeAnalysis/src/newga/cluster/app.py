import numpy as np
from PyQt5.QtGui import QColor, QPixmap, QIcon
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QListWidget, QListWidgetItem, \
    QGridLayout, QBoxLayout
from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.widgets import LassoSelector

from newga.cluster.app_classes import ClusterManager

MAX_GROUPS = 10


def make_figure_and_canvas():
    figure = Figure()
    canvas = FigureCanvas(figure)
    return figure, canvas


class ApplicationWindow(QWidget):
    def __init__(self, data_loader, data_exporter, pca_reducer, mds_reducer):
        super().__init__()
        # GUI elements
        self.button_mds = None
        self.button_pca = None
        self.canvas_dim_reduction = None
        self.figure_dim_reduction = None
        self.button_delete_group = None
        self.widget_group_list = None
        self.button_new_group = None

        # Dependency injection
        self.data_loader = data_loader
        self.data_exporter = data_exporter
        self.pca_reducer = pca_reducer
        self.mds_reducer = mds_reducer

        # Instance variables - dim reduction
        self.reduced_points_for_reducer = None
        self.current_reducer = None
        self.reduced_points_for_reducer = {}
        self.high_dim_points_for_channels = self.data_loader.load_data()

        # Instance variables - clusters and management
        self.cluster_manager = ClusterManager()
        self.lasso = None
        self.current_cluster = 1  # The group that will be assigned to the next selection
        self.num_clusters = 2  # Including the default cluster (no cluster)
        self.clusters_for_channels = None  # An array that stores the group number of each point

        # Process Data
        self.reduced_points_for_reducer = self.cluster_manager.reduce_data([self.pca_reducer, self.mds_reducer],
                                                                           self.high_dim_points_for_channels)

        # Create GUI
        self.create_gui()

    def create_gui(self) -> None:
        # Create the GUI panels
        top_panel = self._make_reducer_mode_panel()
        right_top_panel = self._make_group_panel()
        left_panel = self._make_plot_panel()
        right_bottom_panel = self._make_export_panel()
        # Layout the panels
        layout = QGridLayout()
        layout.addLayout(top_panel, 0, 0, 1, 2)
        layout.addLayout(right_top_panel, 1, 1)
        layout.addWidget(left_panel, 1, 0)
        layout.addLayout(right_bottom_panel, 2, 1)
        # Set stretch factors
        layout.setColumnStretch(0, 3)  # Set stretch factor for column 0 (canvas column) to 3
        layout.setColumnStretch(1, 1)  # Set stretch factor for column 1 (group_panel column) to 1
        self.setLayout(layout)

    def plot(self, reducer) -> None:
        self.cluster_manager.init_clusters_for_channels(reducer, self.current_reducer)
        colors_per_point = self.cluster_manager.assign_cmap_colors_to_channels_based_on_cluster(
            self.reduced_points_for_reducer[reducer])
        reduced_points_x_y = self.prep_reduced_points_for_plotting(reducer)
        ax = self.plot_reduced_points(reduced_points_x_y, colors_per_point)
        self.handle_lasso_selection(ax)
        self.draw_group_list()

    def handle_lasso_selection(self, ax) -> None:
        if self.lasso is not None:
            self.lasso.disconnect_events()
        self.lasso = CustomLassoSelector(ax, self.on_lasso_select)

    def plot_reduced_points(self, reduced_points_x_y, colors_per_point):
        # Plot the reduced data
        self.figure_dim_reduction.clear()
        ax = self.figure_dim_reduction.subplots()
        # Scatter plot
        ax.scatter(reduced_points_x_y[:, 0], reduced_points_x_y[:, 1], c=colors_per_point,
                   cmap=self.cluster_manager.color_map)
        self.canvas_dim_reduction.draw()
        return ax

    def prep_reduced_points_for_plotting(self, reducer):
        # Concatenate the reduced data arrays along the first axis
        reduced_points_for_channels = self.reduced_points_for_reducer[reducer]
        reduced_data_values = np.vstack(list(reduced_points_for_channels.values()))
        return reduced_data_values

    def _make_export_panel(self):
        button_export = self.make_export_button()
        export_panel = QVBoxLayout()
        export_panel.addWidget(button_export)
        return export_panel

    def _make_plot_panel(self):
        self.figure_dim_reduction, self.canvas_dim_reduction = make_figure_and_canvas()
        return self.canvas_dim_reduction

    def make_export_button(self) -> QPushButton:
        export_button = QPushButton('Export')
        export_button.clicked.connect(self.on_export)
        return export_button

    def _make_reducer_mode_panel(self) -> QBoxLayout:
        # Add PCA button
        self.button_pca = self.make_pca_button()
        # Add MDS button
        self.button_mds = self.make_mds_button()
        top_button_panel = QHBoxLayout()
        top_button_panel.addWidget(self.button_pca)
        top_button_panel.addWidget(self.button_mds)
        return top_button_panel

    def make_mds_button(self) -> QPushButton:
        button_mds = QPushButton('MDS', self)
        button_mds.clicked.connect(self.on_mds)  # connect button click to function
        return button_mds

    def make_pca_button(self) -> QPushButton:
        button_pca = QPushButton('PCA', self)
        button_pca.clicked.connect(self.on_pca)  # connect button click to function
        return button_pca

    def _make_group_panel(self) -> QBoxLayout:
        self.widget_group_list = self.make_group_list()
        self.button_new_group = self.make_new_group_button()
        self.button_delete_group = self.make_delete_group_button()
        group_panel = QVBoxLayout()
        group_panel.addWidget(self.button_new_group)
        group_panel.addWidget(self.button_delete_group)
        group_panel.addWidget(self.widget_group_list)
        return group_panel

    def make_delete_group_button(self) -> QPushButton:
        delete_group_button = QPushButton('Delete Group')
        delete_group_button.clicked.connect(self.delete_cluster)
        return delete_group_button

    def make_new_group_button(self) -> QPushButton:
        new_group_button = QPushButton('New Group')
        new_group_button.clicked.connect(self.new_group)
        return new_group_button

    def make_group_list(self) -> QListWidget:
        group_list = QListWidget()
        group_list.itemClicked.connect(self.on_group_selected)
        return group_list

    # def reduce_data(self) -> None:
    #     ndim_points = list(self.high_dim_points_for_channels.values())
    #     # Concatenate all the data into a single 2D array
    #     stacked_points = np.vstack(ndim_points)
    #     for reducer in [self.pca_reducer, self.mds_reducer]:
    #         # Perform dimensionality reduction on all data
    #         all_reduced_data = reducer.fit_transform(stacked_points)
    #
    #         # Split the reduced data back up into channels
    #         reduced_data_for_channels = {}
    #         start_index = 0
    #         for channel_index, channel in enumerate(self.high_dim_points_for_channels.keys()):
    #             # Extract the part of all_reduced_data that corresponds to this channel
    #             reduced_data = all_reduced_data[channel_index, :]
    #             reduced_data_for_channels[channel] = reduced_data
    #
    #         self.reduced_points_for_reducer[reducer] = reduced_data_for_channels

    def on_pca(self) -> None:
        # Run PCA and plot the result
        self.plot(self.pca_reducer)
        self.current_reducer = self.pca_reducer

    def on_mds(self) -> None:
        # Run MDS and plot the result
        self.plot(self.mds_reducer)
        self.current_reducer = self.mds_reducer

    # def _assign_cmap_colors_to_channels_based_on_cluster(self) -> list[float]:
    #     cmap_color_per_channel = []
    #     for channel, data in self.high_dim_points_for_channels.items():
    #         assigned_cluster_for_current_channel = self.clusters_for_channels[channel]
    #         cmap_color_per_channel.append(self.get_cmap_color_for_group(assigned_cluster_for_current_channel))
    #     return cmap_color_per_channel

    def _init_clusters_for_channels(self, reducer) -> None:
        # Reset groups if the reducer has changed
        if self.current_reducer != reducer:
            self.clusters_for_channels = None
            self.current_cluster = 1
        if self.clusters_for_channels is None:
            # Initialize the groups array the first time plot() is called
            self.clusters_for_channels = {channel: 0 for channel in self.high_dim_points_for_channels.keys()}

    # def get_qcolor_for_cluster(self, i) -> QColor:
    #     color = self.cluster_manager.get_cmap_color_for_cluster(i)
    #     color = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))  # Convert to QColor
    #     return color

    # def get_cmap_color_for_group(self, i) -> float:
    #     color = self.color_map(i / MAX_GROUPS)  # Calculate the color of this group
    #     return color

    def new_group(self) -> None:
        # Increment current_group, but don't assign it to any points yet
        self.cluster_manager.add_cluster()
        self.current_cluster += 1
        self.draw_group_list()

    def draw_group_list(self) -> None:
        self.widget_group_list.clear()
        for i in range(self.cluster_manager.num_clusters):
            color = self.cluster_manager.get_qcolor_for_cluster(i)
            pixmap = QPixmap(20, 20)
            pixmap.fill(color)
            icon = QIcon(pixmap)
            if i == 0:
                item = QListWidgetItem(icon, 'Ungrouped')
            else:
                item = QListWidgetItem(icon, 'Group {}'.format(i))
            self.widget_group_list.addItem(item)

    def delete_cluster(self) -> None:
        # Remove the current group from the groups array and the group list
        current_row = self.widget_group_list.currentRow()
        self.widget_group_list.takeItem(current_row)
        self.cluster_manager.delete_cluster(current_row)
        self.draw_group_list()
        self.current_cluster -= 1
        self.plot(self.current_reducer)

    # def delete_cluster(self) -> None:
    #     # Remove the current group from the groups array and the group list
    #     current_row = self.widget_group_list.currentRow()
    #     self.widget_group_list.takeItem(current_row)
    #     self.clusters_for_channels[self.clusters_for_channels == current_row] = 0
    #     self.current_cluster -= 1
    #     self.num_clusters -= 1
    #     # Decrement the group numbers of all higher-numbered groups
    #     for i in range(current_row + 1, self.current_cluster + 1):
    #         self.clusters_for_channels[self.clusters_for_channels == i] = i - 1
    #     self.draw_group_list()
    #     self.plot(self.current_reducer)

    def on_lasso_select(self, verts) -> None:
        path = Path(verts)
        selected_channels = []

        for channel, data in self.cluster_manager.reduced_points_for_reducer[self.current_reducer].items():
            point = data  # since each channel corresponds to one point
            if path.contains_point(point):
                selected_channels.append(channel)

        # Check the mouse button used for lasso selection
        if self.lasso.button == 1:  # Left-click
            # Add selected points to the current group
            self.clusters_for_channels = self.cluster_manager.add_channels_to_cluster(selected_channels, self.current_cluster)
        elif self.lasso.button == 3:  # Right-click
            # Remove selected points from the current group
            self.clusters_for_channels = self.cluster_manager.remove_channels_from_cluster(selected_channels, self.current_cluster)

        self.plot(self.current_reducer)

    # def on_lasso_select(self, verts) -> None:
    #     path = Path(verts)
    #     selected_channels = []
    #
    #     for channel, data in self.reduced_points_for_reducer[self.current_reducer].items():
    #         point = data  # since each channel corresponds to one point
    #         if path.contains_point(point):
    #             selected_channels.append(channel)
    #
    #     # Check the mouse button used for lasso selection
    #     if self.lasso.button == 1:  # Left-click
    #         # Add selected points to the current group
    #         for channel in selected_channels:
    #             self.clusters_for_channels[channel] = self.current_cluster
    #     elif self.lasso.button == 3:  # Right-click
    #         # Remove selected points from the current group
    #         for channel in selected_channels:
    #             if self.clusters_for_channels[channel] == self.current_cluster:
    #                 self.clusters_for_channels[channel] = 0
    #
    #     self.plot(self.current_reducer)

    def on_group_selected(self, item) -> None:
        # Set the current group to the selected group
        self.current_cluster = self.widget_group_list.row(item)

    def on_export(self) -> None:
        channels_for_clusters = {}
        for channel, group in self.clusters_for_channels.items():
            channels_for_clusters[group] = channels_for_clusters.get(group, []) + [channel]
        self.data_exporter.export_data(channels_for_clusters)


class CustomLassoSelector(LassoSelector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button = None

    def press(self, event):
        self.button = event.button
        super().press(event)

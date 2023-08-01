from functools import partial

import numpy as np
from PyQt5.QtGui import QColor, QPixmap, QIcon
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QListWidget, QListWidgetItem, \
    QGridLayout, QBoxLayout
from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.widgets import LassoSelector

from intan.channels import Channel
from newga.cluster.app_classes import ClusterManager
from newga.cluster.dimensionality_reduction import DimensionalityReducer

MAX_GROUPS = 10


def make_figure_and_canvas():
    figure = Figure()
    canvas = FigureCanvas(figure)
    return figure, canvas


class ApplicationWindow(QWidget):
    def __init__(self, data_loader, data_exporter, reducers: list[DimensionalityReducer]):
        super().__init__()
        # GUI elements
        self.button_mds = None
        self.button_pca = None
        self.canvas_dim_reduction = None
        self.figure_dim_reduction = None
        self.button_delete_group = None
        self.widget_cluster_list = None
        self.button_new_group = None

        # Dependency injection
        self.data_loader = data_loader
        self.data_exporter = data_exporter
        self.reducers = reducers

        # Instance variables - dim reduction
        self.channels = None
        self.reduced_points_for_reducer = None
        self.current_reducer = None
        self.reduced_points_for_reducer = {}
        self.high_dim_points_for_channels = self.data_loader.load_data()

        # Process Data
        self.reduced_points_for_reducer = self.reduce_data(self.reducers,
                                                           self.high_dim_points_for_channels)

        # Instance variables - cluster management
        self.lasso = None
        self.current_cluster = 1
        self.clusters_for_channels = None  # An array that stores the group number of each point
        # noinspection PyTypeChecker
        self.cluster_manager = ClusterManager(self.channels)

        # Create GUI
        self.create_gui()

    def reduce_data(self, reducers, point_to_reduce_for_channels: dict[Channel, list[np.ndarray]]):
        high_dim_points = list(point_to_reduce_for_channels.values())
        # Concatenate all the data into a single 2D array
        stacked_points = np.vstack(high_dim_points)
        reduced_points_for_reducer = {}
        for reducer in reducers:
            # Perform dimensionality reduction on all data
            all_reduced_data = reducer.fit_transform(stacked_points)

            # Split the reduced data back up into channels
            reduced_data_for_channels = {}
            self.channels = list(point_to_reduce_for_channels.keys())
            for channel_index, channel in enumerate(self.channels):
                reduced_data = all_reduced_data[channel_index, :]
                reduced_data_for_channels[channel] = reduced_data
            reduced_points_for_reducer[reducer] = reduced_data_for_channels
        return reduced_points_for_reducer

    def create_gui(self) -> None:
        # Create the GUI panels
        top_panel = self.make_reducer_mode_panel()
        right_top_panel = self.make_cluster_control_panel()
        left_panel = self.make_plot_panel()
        right_bottom_panel = self.make_export_panel()
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
        if self.clusters_for_channels is None:
            self.clusters_for_channels = self.cluster_manager.init_clusters_for_channels_from()

        colors_per_point = self.cluster_manager.get_colormap_colors_per_channel_based_on_cluster()

        reduced_points_x_y = self._prep_reduced_points_for_plotting(reducer)
        ax = self._plot_reduced_points(reduced_points_x_y, colors_per_point)
        self._handle_lasso_selection(ax)
        self._draw_group_list()

    def _handle_lasso_selection(self, ax) -> None:
        if self.lasso is not None:
            self.lasso.disconnect_events()
        self.lasso = CustomLassoSelector(ax, self.on_lasso_select)

    def _plot_reduced_points(self, reduced_points_x_y, colors_per_point):
        # Plot the reduced data
        self.figure_dim_reduction.clear()
        ax = self.figure_dim_reduction.subplots()
        # Scatter plot
        ax.scatter(reduced_points_x_y[:, 0], reduced_points_x_y[:, 1], c=colors_per_point,
                   cmap=self.cluster_manager.color_map)
        self.canvas_dim_reduction.draw()
        return ax

    def _prep_reduced_points_for_plotting(self, reducer):
        # Concatenate the reduced data arrays along the first axis
        reduced_points_for_channels = self.reduced_points_for_reducer[reducer]
        reduced_data_values = np.vstack(list(reduced_points_for_channels.values()))
        return reduced_data_values

    def make_export_panel(self):
        button_export = self._make_export_button()
        export_panel = QVBoxLayout()
        export_panel.addWidget(button_export)
        return export_panel

    def make_plot_panel(self):
        self.figure_dim_reduction, self.canvas_dim_reduction = make_figure_and_canvas()
        return self.canvas_dim_reduction

    def _make_export_button(self) -> QPushButton:
        export_button = QPushButton('Export')
        export_button.clicked.connect(self.on_export)
        return export_button

    def make_reducer_mode_panel(self) -> QBoxLayout:
        buttons = []
        for reducer in self.reducers:
            reducer_button = self._make_reducer_button(reducer.get_name(), reducer)
            buttons.append(reducer_button)

        top_button_panel = QHBoxLayout()
        for button in buttons:
            top_button_panel.addWidget(button)
        return top_button_panel

    def _make_reducer_button(self, reducer_name: str, reducer: DimensionalityReducer) -> QPushButton:
        button = QPushButton(reducer_name)
        button.clicked.connect(partial(self._on_reducer, reducer))
        return button

    def _on_reducer(self, reducer: DimensionalityReducer):
        self.plot(reducer)
        self.current_reducer = reducer

    def make_cluster_control_panel(self) -> QBoxLayout:
        self.widget_cluster_list = self._make_group_list()
        self.button_new_group = self._make_new_group_button()
        self.button_delete_group = self._make_delete_group_button()
        group_panel = QVBoxLayout()
        group_panel.addWidget(self.button_new_group)
        group_panel.addWidget(self.button_delete_group)
        group_panel.addWidget(self.widget_cluster_list)
        return group_panel

    def _make_delete_group_button(self) -> QPushButton:
        delete_group_button = QPushButton('Delete Group')
        delete_group_button.clicked.connect(self.on_delete_cluster)
        return delete_group_button

    def _make_new_group_button(self) -> QPushButton:
        new_group_button = QPushButton('New Group')
        new_group_button.clicked.connect(self.on_new_group)
        return new_group_button

    def _make_group_list(self) -> QListWidget:
        group_list = QListWidget()
        group_list.itemClicked.connect(self.on_group_selected)
        return group_list

    def on_new_group(self) -> None:
        # Increment current_group, but don't assign it to any points yet
        self.cluster_manager.add_cluster()
        self.current_cluster += 1
        self._draw_group_list()

    def _draw_group_list(self) -> None:
        self.widget_cluster_list.clear()
        for i in range(self.cluster_manager.num_clusters):
            color = self.cluster_manager.get_qcolor_for_cluster(i)
            pixmap = QPixmap(20, 20)
            pixmap.fill(color)
            icon = QIcon(pixmap)
            if i == 0:
                item = QListWidgetItem(icon, 'Ungrouped')
            else:
                item = QListWidgetItem(icon, 'Group {}'.format(i))
            self.widget_cluster_list.addItem(item)

    def on_delete_cluster(self) -> None:
        # Remove the current group from the groups array and the group list
        current_row = self.widget_cluster_list.currentRow()
        self.widget_cluster_list.takeItem(current_row)
        self.clusters_for_channels = self.cluster_manager.delete_cluster(current_row)
        self.current_cluster = 1
        self._draw_group_list()
        self.plot(self.current_reducer)

    def on_lasso_select(self, verts) -> None:
        path = Path(verts)
        selected_channels = []

        for channel, data in self.reduced_points_for_reducer[self.current_reducer].items():
            point = data  # since each channel corresponds to one point
            if path.contains_point(point):
                selected_channels.append(channel)

        # Check the mouse button used for lasso selection
        if self.lasso.button == 1:  # Left-click
            # Add selected points to the current group
            self.clusters_for_channels = self.cluster_manager.add_channels_to_cluster(selected_channels,
                                                                                      self.current_cluster)
        elif self.lasso.button == 3:  # Right-click
            # Remove selected points from the current group
            self.clusters_for_channels = self.cluster_manager.remove_channels_from_cluster(selected_channels,
                                                                                           self.current_cluster)

        self.plot(self.current_reducer)

    def on_group_selected(self, item) -> None:
        # Set the current group to the selected group
        self.current_cluster = self.widget_cluster_list.row(item)

    def on_export(self) -> None:
        channels_for_clusters = {}
        for channel, cluster in self.clusters_for_channels.items():
            channels_for_clusters[cluster] = channels_for_clusters.get(cluster, []) + [channel]
        self.data_exporter.export_data(channels_for_clusters)


class CustomLassoSelector(LassoSelector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button = None

    def press(self, event):
        self.button = event.button
        super().press(event)

from functools import partial

import numpy as np
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QListWidget, QListWidgetItem, \
    QGridLayout, QBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.widgets import LassoSelector, RectangleSelector

from clat.intan.channels import Channel
from pga.gui.cluster.cluster_app_classes import ClusterManager, DataLoader, DataExporter, ChannelMapper, Annotator
from pga.gui.cluster.dimensionality_reduction import DimensionalityReducer

MAX_GROUPS = 10


def make_figure_and_canvas():
    figure = Figure()
    canvas = FigureCanvas(figure)
    return figure, canvas


class ClusterApplicationWindow(QWidget):
    def __init__(self, data_loader: DataLoader, data_exporter: DataExporter, reducers: list[DimensionalityReducer],
                 channel_mapper: ChannelMapper):
        super().__init__()
        # GUI elements
        self.channel_labels_dim_reduction = None
        self.channel_labels_channel_map = None
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
        self.channel_mapper = channel_mapper

        # Instance variables - dim reduction
        self.channels = None
        self.reduced_points_for_reducer = None
        self.current_reducer = None
        self.reduced_points_for_reducer = {}
        self.high_dim_points_for_channels = self.data_loader.load_data_for_channels()

        # Process Data
        self.reduced_points_for_reducer = self.reduce_data(self.reducers,
                                                           self.high_dim_points_for_channels)

        # Instance variables - cluster management
        self.lasso_selector_for_dim_reduction = None
        self.rectangle_selector_for_channel_mapping = None
        self.current_cluster = 1
        self.clusters_for_channels = None  # An array that stores the group number of each point
        # noinspection PyTypeChecker
        self.cluster_manager = ClusterManager(self.channels)

        # Create GUI
        self.create_gui()

        # Annotations
        self.annotator = Annotator()

    def reduce_data(self, reducers: list[DimensionalityReducer],
                    point_to_reduce_for_channels: dict[Channel, np.ndarray]):
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
        top_panel = self._make_reducer_mode_panel()
        right_top_panel = self._make_cluster_control_panel()
        middle_panel = self._make_dim_reduction_panel()
        left_panel = self._make_channel_mapping_panel()

        right_bottom_panel = self._make_export_panel()
        # Layout the panels
        layout = QGridLayout()
        layout.addLayout(top_panel, 0, 0, 1, 3)
        layout.addLayout(right_top_panel, 1, 2)
        layout.addWidget(middle_panel, 1, 1)
        layout.addWidget(left_panel, 1, 0)
        layout.addLayout(right_bottom_panel, 2, 2)
        # Set stretch factors
        layout.setColumnStretch(0, 1)  # Set stretch factor for column 0 (canvas column) to 3
        layout.setColumnStretch(1, 3)  # Set stretch factor for column 1 (group_panel column) to 1
        layout.setColumnStretch(2, 1)  # Set stretch factor for column 1 (group_panel column) to 1
        self.setLayout(layout)

    def _make_dim_reduction_panel(self) -> QWidget:
        self.figure_dim_reduction, self.canvas_dim_reduction = make_figure_and_canvas()
        # Connect the hover event to the function _update_annotation
        self.canvas_dim_reduction.mpl_connect("pick_event", self.on_pick_dim_reduction)
        self.canvas_dim_reduction.mpl_connect("figure_leave_event", self.on_leave_dim_reduction)
        return self.canvas_dim_reduction

    def _make_export_panel(self) -> QBoxLayout:
        button_export = self._make_export_button()
        export_panel = QVBoxLayout()
        export_panel.addWidget(button_export)
        return export_panel

    def _make_export_button(self) -> QPushButton:
        export_button = QPushButton('Export')
        export_button.clicked.connect(self.on_export)
        return export_button

    def _make_reducer_mode_panel(self) -> QBoxLayout:
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
        button.clicked.connect(partial(self.on_reducer, reducer))
        return button

    def _make_cluster_control_panel(self) -> QBoxLayout:
        self.widget_cluster_list = self._make_group_list()
        self.button_new_group = self._make_new_cluster_button()
        self.button_delete_group = self._make_delete_cluster_button()
        group_panel = QVBoxLayout()
        group_panel.addWidget(self.button_new_group)
        group_panel.addWidget(self.button_delete_group)
        group_panel.addWidget(self.widget_cluster_list)
        return group_panel

    def _make_new_cluster_button(self) -> QPushButton:
        new_cluster_button = QPushButton('New Cluster')
        new_cluster_button.clicked.connect(self.on_new_cluster)
        return new_cluster_button

    def _make_delete_cluster_button(self) -> QPushButton:
        delete_cluster_button = QPushButton('Delete Cluster')
        delete_cluster_button.clicked.connect(self.on_delete_cluster)
        return delete_cluster_button

    def _make_group_list(self) -> QListWidget:
        group_list = QListWidget()
        group_list.itemClicked.connect(self.on_cluster_selected)
        return group_list

    def _make_channel_mapping_panel(self):
        # Create a new Figure and FigureCanvas for the channel map plot
        self.figure_channel_map, self.canvas_channel_map = make_figure_and_canvas()
        self.canvas_channel_map.mpl_connect("pick_event", self.on_pick_channel_map)
        self.canvas_channel_map.mpl_connect("figure_leave_event", self.on_leave_channel_map)
        return self.canvas_channel_map

    def plot(self, reducer: DimensionalityReducer) -> None:
        if self.clusters_for_channels is None:
            self.clusters_for_channels = self.cluster_manager.init_clusters_for_channels()

        dim_reduction_ax = self._plot_dim_reduction(reducer)
        channel_map_ax = self._plot_channel_map()
        self._handle_dim_reduction_lasso_selection(dim_reduction_ax)
        self._handle_channel_mapping_selection(channel_map_ax)
        self._draw_cluster_list()

    def _plot_dim_reduction(self, reducer):
        colors_per_point = self.cluster_manager.get_colormap_colors_per_channel_based_on_cluster()
        reduced_points_x_y = self._prep_reduced_points_for_plotting(reducer)
        dim_reduction_ax = self._plot_clustered_scatter(reduced_points_x_y, colors_per_point)
        return dim_reduction_ax

    def _prep_reduced_points_for_plotting(self, reducer: DimensionalityReducer):
        # Concatenate the reduced data arrays along the first axis
        reduced_points_for_channels = self.reduced_points_for_reducer[reducer]
        reduced_data_values = np.vstack(list(reduced_points_for_channels.values()))
        return reduced_data_values

    def _plot_clustered_scatter(self, reduced_points_x_y: np.ndarray, colors_per_point: list[float]):
        # Plot the reduced data
        self.figure_dim_reduction.clear()
        self.scatter_dim_reduction = self.figure_dim_reduction.subplots()

        # Scatter plot with picker enabled
        self.scatter_dim_reduction.scatter(reduced_points_x_y[:, 0], reduced_points_x_y[:, 1], c=colors_per_point,
                                           cmap=self.cluster_manager.color_map, picker=True)

        # Create the annotation for this plot
        self.channel_labels_dim_reduction = self.annotator.init_annotations(self.scatter_dim_reduction)

        self.canvas_dim_reduction.draw()
        return self.scatter_dim_reduction

    def _plot_channel_map(self):
        # Clear the previous plot
        self.figure_channel_map.clear()
        self.scatter_channel_map = self.figure_channel_map.subplots()

        # Get the colors for each channel based on its cluster
        colors_per_point = self.cluster_manager.get_colormap_colors_per_channel_based_on_cluster()

        # Plot each channel at its mapped coordinates
        x = [self.channel_mapper.get_coordinates(channel)[0] for channel in self.channels]
        y = [self.channel_mapper.get_coordinates(channel)[1] for channel in self.channels]
        self.scatter_channel_map.scatter(x, y, c=colors_per_point, picker=True)

        self.channel_labels_channel_map = self.annotator.init_annotations(self.scatter_channel_map)

        self.canvas_channel_map.draw()
        return self.scatter_channel_map

    def _handle_dim_reduction_lasso_selection(self, ax) -> None:
        if self.lasso_selector_for_dim_reduction is not None:
            self.lasso_selector_for_dim_reduction.disconnect_events()
        self.lasso_selector_for_dim_reduction = CustomLassoSelector(ax, self.on_dim_reduction_lasso_select)

    def _handle_channel_mapping_selection(self, ax) -> None:
        if self.rectangle_selector_for_channel_mapping is not None:
            self.rectangle_selector_for_channel_mapping.disconnect_events()
        self.rectangle_selector_for_channel_mapping = CustomRectangleSelector(ax,
                                                                              self.on_channel_map_rectangle_selector)

    def on_pick_dim_reduction(self, event):
        ind = event.ind[0]  # Get the index of the point
        x, y = event.artist.get_offsets().data[ind]  # Get the coordinates of the point
        channel_label = str(self.channels[ind]).split('.')[-1]
        self.annotator.show_annotation_at(x, y, channel_label, self.channel_labels_dim_reduction)

        # Show the corresponding annotation on the channel_map plot
        x_map, y_map = self.channel_mapper.get_coordinates(self.channels[ind])
        self.annotator.show_annotation_at(x_map, y_map, channel_label, self.channel_labels_channel_map)

        self.canvas_dim_reduction.draw()
        self.canvas_channel_map.draw()

    def on_leave_dim_reduction(self, event):
        # This function is called when the mouse leaves the figure
        # Hide the annotation
        self.annotator.hide_annotations_for(self.channel_labels_dim_reduction)
        self.annotator.hide_annotations_for(self.channel_labels_channel_map)
        self.canvas_channel_map.draw()
        self.canvas_dim_reduction.draw()

    def on_pick_channel_map(self, event):
        channel_indx = event.ind[0]  # Get the index of the point
        x, y = event.artist.get_offsets().data[channel_indx]  # Get the coordinates of the point
        channel_label = str(self.channels[channel_indx]).split('.')[-1]
        self.annotator.show_annotation_at(x, y, channel_label, self.channel_labels_channel_map)

        # Show the corresponding annotation on the dim_reduction plot
        x_dim, y_dim = self.reduced_points_for_reducer[self.current_reducer][self.channels[channel_indx]]
        self.annotator.show_annotation_at(x_dim, y_dim, channel_label, self.channel_labels_dim_reduction)

        self.canvas_dim_reduction.draw()
        self.canvas_channel_map.draw()

    def on_leave_channel_map(self, event):
        # This function is called when the mouse leaves the figure
        self.annotator.hide_annotations_for(self.channel_labels_channel_map)
        self.annotator.hide_annotations_for(self.channel_labels_dim_reduction)
        self.canvas_channel_map.draw()
        self.canvas_dim_reduction.draw()

    def on_reducer(self, reducer: DimensionalityReducer):
        self.plot(reducer)
        self.current_reducer = reducer

    def on_new_cluster(self) -> None:
        # Increment current_group, but don't assign it to any points yet
        self.cluster_manager.add_cluster()
        self.current_cluster = self.cluster_manager.num_clusters - 1
        self._draw_cluster_list()

    def _draw_cluster_list(self) -> None:
        self.widget_cluster_list.clear()
        for i in range(self.cluster_manager.num_clusters):
            color = self.cluster_manager.get_qcolor_for_cluster(i)
            pixmap = QPixmap(20, 20)
            pixmap.fill(color)
            icon = QIcon(pixmap)
            if i == 0:
                item = QListWidgetItem(icon, 'No Cluster')
            else:
                item = QListWidgetItem(icon, 'Cluster {}'.format(i))
            self.widget_cluster_list.addItem(item)

    def on_delete_cluster(self) -> None:
        current_row = self.widget_cluster_list.currentRow()
        self.widget_cluster_list.takeItem(current_row)
        self.clusters_for_channels = self.cluster_manager.delete_cluster(current_row)
        self.current_cluster = current_row - 1
        self._draw_cluster_list()
        self.plot(self.current_reducer)

    def on_dim_reduction_lasso_select(self, verts: list[int]) -> None:
        path = Path(verts)
        selected_channels = []

        for channel, data in self.reduced_points_for_reducer[self.current_reducer].items():
            point = data  # since each channel corresponds to one point
            if path.contains_point(point):
                selected_channels.append(channel)

        # Check the mouse button used for lasso selection
        if self.lasso_selector_for_dim_reduction.button == 1:  # Left-click
            # Add selected points to the current group
            self.clusters_for_channels = self.cluster_manager.add_channels_to_cluster(selected_channels,
                                                                                      self.current_cluster)
        elif self.lasso_selector_for_dim_reduction.button == 3:  # Right-click
            # Remove selected points from the current group
            self.clusters_for_channels = self.cluster_manager.remove_channels_from_cluster(selected_channels,
                                                                                           self.current_cluster)

        self.plot(self.current_reducer)

    def on_channel_map_rectangle_selector(self, eclick, erelease) -> None:
        # This method is called when the RectangleSelector captures a selection
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        selected_channels = []
        for i, channel in enumerate(self.channels):
            x, y = self.channel_mapper.get_coordinates(channel)
            if min(x1, x2) < x < max(x1, x2) and min(y1, y2) < y < max(y1, y2):
                # If the channel is inside the rectangle, add it to the selected channels
                selected_channels.append(channel)

        if self.rectangle_selector_for_channel_mapping.button == 1:  # Left-click
            # Add selected points to the current group
            self.clusters_for_channels = self.cluster_manager.add_channels_to_cluster(selected_channels,
                                                                                      self.current_cluster)
        elif self.rectangle_selector_for_channel_mapping.button == 3:  # Right-click
            # Remove selected points from the current group
            self.clusters_for_channels = self.cluster_manager.remove_channels_from_cluster(selected_channels,
                                                                                           self.current_cluster)

        self.plot(self.current_reducer)

    def on_cluster_selected(self, item) -> None:
        # Set the current group to the selected group
        self.current_cluster = self.widget_cluster_list.row(item)

    def on_export(self) -> None:
        channels_for_clusters = {}
        for channel, cluster in self.clusters_for_channels.items():
            channels_for_clusters[cluster] = channels_for_clusters.get(cluster, []) + [channel]
        self.data_exporter.export_channels_for_clusters(channels_for_clusters)


class CustomLassoSelector(LassoSelector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button = None

    def press(self, event):
        self.button = event.button
        super().press(event)


class CustomRectangleSelector(RectangleSelector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button = None

    def press(self, event):
        self.button = event.button
        super().press(event)

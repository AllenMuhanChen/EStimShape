from functools import partial

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QListWidget, QListWidgetItem, \
    QGridLayout, QBoxLayout, QLabel, QSlider, QSpinBox, QCheckBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.widgets import LassoSelector, RectangleSelector
# Importing mplot3d registers the '3d' projection used for the optional 3D view.
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from clat.intan.channels import Channel
from src.cluster.cluster_app_classes import ClusterManager, DataLoader, DataExporter, ChannelMapper, Annotator, \
    ClusterLoader
from src.cluster.dimensionality_reduction import DimensionalityReducer

MAX_GROUPS = 10

# How many components to compute for each reducer so the user can browse beyond
# the first two PCs. Clamped per-reducer to the data dimensions (and to each
# reducer's own max_components) in reduce_data.
DEFAULT_N_COMPONENTS = 10


def make_figure_and_canvas():
    figure = Figure()
    canvas = FigureCanvas(figure)
    return figure, canvas


class ClusterApplicationWindow(QWidget):
    def __init__(self, data_loader: DataLoader, data_exporter: DataExporter, reducers: list[DimensionalityReducer],
                 channel_mapper: ChannelMapper, cluster_loader: ClusterLoader = None):
        super().__init__()
        # GUI elements
        self.channel_labels_dim_reduction = None
        self.channel_labels_channel_map = None
        self.button_mds = None
        self.button_pca = None
        self.canvas_dim_reduction = None
        self.figure_dim_reduction = None
        self.canvas_variance = None
        self.figure_variance = None
        self.spin_x_axis = None
        self.spin_y_axis = None
        self.spin_z_axis = None
        self.checkbox_3d = None
        self.button_delete_group = None
        self.widget_cluster_list = None
        self.button_new_group = None
        self.label_gen_info = None
        self.button_reload_data = None
        self.slider_generation = None
        self.label_gen_cutoff = None

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

        # Which components (0-indexed) are shown on each axis, and whether the
        # scatter is drawn in 3D. Defaults: PC1 vs PC2 (vs PC3 when in 3D).
        self.x_axis_idx = 0
        self.y_axis_idx = 1
        self.z_axis_idx = 2
        self.is_3d = False

        # Generation segmentation: load all data initially, and find the latest generation
        self.max_generation = self.data_loader.get_max_generation()
        self.gen_cutoff = self.max_generation
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
        self.loaded_gen_id = None

        # Load existing cluster if available
        if cluster_loader is not None:
            loaded = cluster_loader.load_current_cluster_info()
            if loaded is not None:
                cluster_channels, gen_id = loaded
                self.cluster_manager.clusters_for_channels = {
                    channel: (1 if channel in cluster_channels else 0)
                    for channel in self.channels
                }
                self.clusters_for_channels = self.cluster_manager.clusters_for_channels
                self.cluster_manager.num_clusters = 2
                self.loaded_gen_id = gen_id

        # Create GUI
        self.create_gui()

        # Annotations
        self.annotator = Annotator()

        # Auto-plot with first reducer if cluster was pre-loaded
        if self.clusters_for_channels is not None and self.reducers:
            self.current_reducer = self.reducers[0]
            self.plot(self.reducers[0])

    def reduce_data(self, reducers: list[DimensionalityReducer],
                    points_to_reduce_for_channels: dict[Channel, np.ndarray]):

        points_to_reduce_for_channels_with_data = self._filter_disabled_channels(points_to_reduce_for_channels)

        high_dim_points = list(points_to_reduce_for_channels_with_data.values())

        # Per-channel z-score normalization
        normalized_points = []
        for points in high_dim_points:
            if len(points) > 1 and np.std(points) > 1e-10:  # Avoid division by zero
                normalized = (points - np.mean(points)) / np.std(points)
            else:
                normalized = points
            normalized_points.append(normalized)

        # Concatenate all the normalized data into a single 2D array
        stacked_points = np.vstack(normalized_points)

        # Number of components is bounded by the data: at most n_samples and
        # at most n_features (PCA/MDS/etc. all require this).
        n_samples, n_features = stacked_points.shape
        data_limit = max(2, min(n_samples, n_features))

        reduced_points_for_reducer = {}
        for reducer in reducers:
            # Compute extra components so the user can browse beyond PC1/PC2,
            # clamped to the data and to this reducer's own ceiling.
            desired = min(DEFAULT_N_COMPONENTS, data_limit)
            if reducer.max_components is not None:
                desired = min(desired, reducer.max_components)
            reducer.n_components = max(2, desired)

            # Perform dimensionality reduction on normalized data
            all_reduced_data = reducer.fit_transform(stacked_points)

            # Split the reduced data back up into channels
            reduced_data_for_channels = {}
            self.channels = list(points_to_reduce_for_channels_with_data.keys())
            for channel_index, channel in enumerate(self.channels):
                reduced_data = all_reduced_data[channel_index, :]
                reduced_data_for_channels[channel] = reduced_data
            reduced_points_for_reducer[reducer] = reduced_data_for_channels
        return reduced_points_for_reducer

    def _filter_disabled_channels(self, points_to_reduce_for_channels):
        points_to_reduce_for_channels_with_data = {}
        for channel, points in points_to_reduce_for_channels.items():
            if len(points) > 0:
                points_to_reduce_for_channels_with_data[channel] = points
        return points_to_reduce_for_channels_with_data

    def create_gui(self) -> None:
        # Create the GUI panels
        top_panel = self._make_reducer_mode_panel()
        right_top_panel = self._make_cluster_control_panel()
        middle_panel = self._make_dim_reduction_panel()
        left_panel = self._make_channel_mapping_panel()

        right_bottom_panel = self._make_export_panel()
        data_control_panel = self._make_data_control_panel()
        # Layout the panels
        layout = QGridLayout()
        layout.addLayout(top_panel, 0, 0, 1, 3)
        layout.addLayout(right_top_panel, 1, 2)
        layout.addWidget(middle_panel, 1, 1)
        layout.addWidget(left_panel, 1, 0)
        layout.addLayout(right_bottom_panel, 2, 2)
        layout.addLayout(data_control_panel, 3, 0, 1, 3)
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

        # Variance-explained (scree) plot, always shown beneath the scatter.
        self.figure_variance, self.canvas_variance = make_figure_and_canvas()
        self.canvas_variance.setMaximumHeight(180)

        axis_controls = self._make_axis_controls()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(axis_controls)
        layout.addWidget(self.canvas_dim_reduction, stretch=4)
        layout.addWidget(self.canvas_variance, stretch=1)
        return container

    def _make_axis_controls(self) -> QBoxLayout:
        """Spin boxes to pick which component is shown on each axis, plus a 2D/3D
        toggle. PC numbers are 1-indexed in the UI (PC1 == component 0)."""
        self.spin_x_axis = self._make_axis_spinbox(self.x_axis_idx + 1)
        self.spin_y_axis = self._make_axis_spinbox(self.y_axis_idx + 1)
        self.spin_z_axis = self._make_axis_spinbox(self.z_axis_idx + 1)
        self.spin_z_axis.setEnabled(False)  # only meaningful in 3D

        self.checkbox_3d = QCheckBox("3D view")
        self.checkbox_3d.setChecked(False)
        self.checkbox_3d.stateChanged.connect(self.on_toggle_3d)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("X axis: PC"))
        controls.addWidget(self.spin_x_axis)
        controls.addWidget(QLabel("Y axis: PC"))
        controls.addWidget(self.spin_y_axis)
        controls.addWidget(QLabel("Z axis: PC"))
        controls.addWidget(self.spin_z_axis)
        controls.addWidget(self.checkbox_3d)
        controls.addStretch(1)
        return controls

    def _make_axis_spinbox(self, value: int) -> QSpinBox:
        spinbox = QSpinBox()
        spinbox.setMinimum(1)
        spinbox.setMaximum(max(value, 2))  # widened to match the data in _update_axis_controls
        spinbox.setValue(value)
        spinbox.valueChanged.connect(self.on_axis_changed)
        return spinbox

    def _num_components_for(self, reducer: DimensionalityReducer) -> int:
        """How many components the given reducer actually produced."""
        reduced_for_channels = self.reduced_points_for_reducer.get(reducer)
        if not reduced_for_channels:
            return 2
        any_point = next(iter(reduced_for_channels.values()))
        return int(len(any_point))

    def _update_axis_controls(self, reducer: DimensionalityReducer) -> None:
        """Cap the spin boxes to the number of components available for the
        current reducer, and re-sync the stored axis indices."""
        n_components = self._num_components_for(reducer)
        for spinbox in (self.spin_x_axis, self.spin_y_axis, self.spin_z_axis):
            if spinbox is None:
                continue
            spinbox.blockSignals(True)
            spinbox.setMaximum(n_components)
            spinbox.blockSignals(False)
        # Spin boxes clamp their own values to the new maximum; read them back.
        self.x_axis_idx = self.spin_x_axis.value() - 1
        self.y_axis_idx = self.spin_y_axis.value() - 1
        self.z_axis_idx = self.spin_z_axis.value() - 1

    def _make_export_panel(self) -> QBoxLayout:
        button_export = self._make_export_button()
        export_panel = QVBoxLayout()
        export_panel.addWidget(button_export)
        return export_panel

    def _make_export_button(self) -> QPushButton:
        export_button = QPushButton('Export')
        export_button.clicked.connect(self.on_export)
        return export_button

    def _make_data_control_panel(self) -> QBoxLayout:
        # Reload button: re-query the data source to pick up newer generations
        self.button_reload_data = QPushButton('Reload Data')
        self.button_reload_data.clicked.connect(self.on_reload_data)

        # Generation slider: include all generations up to and including the slider value.
        # Far right = all generations; far left = only generation 1.
        self.slider_generation = QSlider(Qt.Horizontal)
        # Block signals during initial setup so we don't trigger a reload/plot before
        # the rest of the window is constructed (data is already loaded for all generations).
        self.slider_generation.blockSignals(True)
        self.slider_generation.setMinimum(1)
        self.slider_generation.setMaximum(max(self.max_generation, 1))
        self.slider_generation.setValue(max(self.max_generation, 1))
        self.slider_generation.setTickPosition(QSlider.TicksBelow)
        self.slider_generation.setTickInterval(1)
        self.slider_generation.setSingleStep(1)
        self.slider_generation.setPageStep(1)
        self.slider_generation.blockSignals(False)
        self.slider_generation.valueChanged.connect(self.on_generation_slider_changed)

        self.label_gen_cutoff = QLabel(self._gen_cutoff_text(max(self.max_generation, 1)))

        data_control_panel = QHBoxLayout()
        data_control_panel.addWidget(self.button_reload_data)
        data_control_panel.addWidget(QLabel("Show generations ≤"))
        data_control_panel.addWidget(self.slider_generation)
        data_control_panel.addWidget(self.label_gen_cutoff)
        return data_control_panel

    def _gen_cutoff_text(self, cutoff: int) -> str:
        if cutoff >= self.max_generation:
            return f"All generations (1–{self.max_generation})"
        return f"Generations 1–{cutoff}"

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
        self.label_gen_info = QLabel(self._gen_info_text())
        group_panel = QVBoxLayout()
        group_panel.addWidget(self.label_gen_info)
        group_panel.addWidget(self.button_new_group)
        group_panel.addWidget(self.button_delete_group)
        group_panel.addWidget(self.widget_cluster_list)
        return group_panel

    def _gen_info_text(self) -> str:
        if self.loaded_gen_id is not None:
            return f"Loaded cluster from generation {self.loaded_gen_id}"
        return "No cluster loaded"

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

        self._update_axis_controls(reducer)
        dim_reduction_ax = self._plot_dim_reduction(reducer)
        self._plot_variance_explained(reducer)
        channel_map_ax = self._plot_channel_map()
        # Lasso selection only works in the 2D scatter; the 3D view is for
        # inspection (rotate/zoom). Clusters can still be edited via the channel
        # map's rectangle selector while in 3D.
        if not self.is_3d:
            self._handle_dim_reduction_lasso_selection(dim_reduction_ax)
        elif self.lasso_selector_for_dim_reduction is not None:
            self.lasso_selector_for_dim_reduction.disconnect_events()
            self.lasso_selector_for_dim_reduction = None
        self._handle_channel_mapping_selection(channel_map_ax)
        self._draw_cluster_list()

    def _plot_dim_reduction(self, reducer):
        colors_per_point = self.cluster_manager.get_colormap_colors_per_channel_based_on_cluster()
        reduced_data_values = self._prep_reduced_points_for_plotting(reducer)
        dim_reduction_ax = self._plot_clustered_scatter(reduced_data_values, colors_per_point)
        return dim_reduction_ax

    def _prep_reduced_points_for_plotting(self, reducer: DimensionalityReducer):
        # Stack the per-channel reduced points into (n_channels, n_components).
        reduced_points_for_channels = self.reduced_points_for_reducer[reducer]
        reduced_data_values = np.vstack(list(reduced_points_for_channels.values()))
        return reduced_data_values

    def _plot_clustered_scatter(self, reduced_data_values: np.ndarray, colors_per_point: list[float]):
        # Plot the reduced data using the user-selected components for each axis.
        self.figure_dim_reduction.clear()
        x_idx, y_idx = self.x_axis_idx, self.y_axis_idx
        x = reduced_data_values[:, x_idx]
        y = reduced_data_values[:, y_idx]

        if self.is_3d:
            z_idx = self.z_axis_idx
            z = reduced_data_values[:, z_idx]
            self.scatter_dim_reduction = self.figure_dim_reduction.add_subplot(projection='3d')
            self.scatter_dim_reduction.scatter(x, y, z, c=colors_per_point,
                                               cmap=self.cluster_manager.color_map, picker=True)
            self.scatter_dim_reduction.set_xlabel(f"PC{x_idx + 1}")
            self.scatter_dim_reduction.set_ylabel(f"PC{y_idx + 1}")
            self.scatter_dim_reduction.set_zlabel(f"PC{z_idx + 1}")
            # Annotations are a 2D-only convenience; skip them in 3D.
            self.channel_labels_dim_reduction = None
        else:
            self.scatter_dim_reduction = self.figure_dim_reduction.subplots()
            self.scatter_dim_reduction.scatter(x, y, c=colors_per_point,
                                               cmap=self.cluster_manager.color_map, picker=True)
            self.scatter_dim_reduction.set_xlabel(f"PC{x_idx + 1}")
            self.scatter_dim_reduction.set_ylabel(f"PC{y_idx + 1}")
            # Create the annotation for this plot
            self.channel_labels_dim_reduction = self.annotator.init_annotations(self.scatter_dim_reduction)

        self.canvas_dim_reduction.draw()
        return self.scatter_dim_reduction

    def _plot_variance_explained(self, reducer: DimensionalityReducer) -> None:
        """Draw a bar chart of variance explained per component, highlighting the
        components currently shown on the axes. Falls back to a message for
        reducers that don't expose explained variance (MDS, TSNE, SparsePCA)."""
        self.figure_variance.clear()
        ax = self.figure_variance.subplots()

        ratios = reducer.get_explained_variance_ratio()
        if ratios is None or len(ratios) == 0:
            ax.text(0.5, 0.5, f"Variance explained not available for {reducer.get_name()}",
                    ha='center', va='center', fontsize=9, color='gray')
            ax.axis('off')
            self.canvas_variance.draw()
            return

        ratios = np.asarray(ratios)
        xs = np.arange(1, len(ratios) + 1)
        selected = {self.x_axis_idx, self.y_axis_idx}
        if self.is_3d:
            selected.add(self.z_axis_idx)
        colors = ['orange' if (i in selected) else 'steelblue' for i in range(len(ratios))]
        ax.bar(xs, ratios, color=colors, edgecolor='black', linewidth=0.5)
        ax.set_xlabel("PC", fontsize=8)
        ax.set_ylabel("Var. expl.", fontsize=8)
        ax.set_title("Variance explained per PC (selected axes highlighted)", fontsize=9)
        ax.set_xticks(xs)
        ax.tick_params(axis='both', labelsize=7)
        self.figure_variance.tight_layout()
        self.canvas_variance.draw()

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
        # Annotations are only drawn in the 2D scatter.
        if self.is_3d or self.channel_labels_dim_reduction is None:
            return
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

        # Show the corresponding annotation on the dim_reduction plot, projected
        # onto the components currently shown on the X and Y axes (2D only).
        point = self.reduced_points_for_reducer[self.current_reducer][self.channels[channel_indx]]
        x_dim, y_dim = point[self.x_axis_idx], point[self.y_axis_idx]
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
        self.current_reducer = reducer
        self.plot(reducer)

    def on_axis_changed(self, _value: int = 0) -> None:
        """Re-plot when the user picks a different component for any axis."""
        self.x_axis_idx = self.spin_x_axis.value() - 1
        self.y_axis_idx = self.spin_y_axis.value() - 1
        self.z_axis_idx = self.spin_z_axis.value() - 1
        if self.current_reducer is not None:
            self.plot(self.current_reducer)

    def on_toggle_3d(self, _state: int = 0) -> None:
        """Toggle between the 2D and 3D scatter views."""
        self.is_3d = self.checkbox_3d.isChecked()
        if self.spin_z_axis is not None:
            self.spin_z_axis.setEnabled(self.is_3d)
        if self.current_reducer is not None:
            self.plot(self.current_reducer)

    def on_reload_data(self) -> None:
        """Re-query the data source to pick up data from newer generations, and refresh
        the generation slider's range to reflect the newly available generations."""
        self.max_generation = self.data_loader.get_max_generation()

        # Refresh the slider range; keep it pinned to the latest generation so the
        # reload shows everything that's now available.
        self.slider_generation.blockSignals(True)
        self.slider_generation.setMaximum(max(self.max_generation, 1))
        self.slider_generation.setValue(max(self.max_generation, 1))
        self.slider_generation.blockSignals(False)

        self.gen_cutoff = self.max_generation
        self._reload_with_gen_cutoff(self.max_generation)

    def on_generation_slider_changed(self, value: int) -> None:
        self.gen_cutoff = value
        self._reload_with_gen_cutoff(value)

    def _reload_with_gen_cutoff(self, cutoff: int) -> None:
        """Reload data including only generations up to and including cutoff, re-run
        dimensionality reduction, and re-plot. Existing cluster assignments are preserved
        for channels that still have data."""
        # Preserve current cluster assignments so segmenting/reloading doesn't wipe them
        old_clusters = dict(self.cluster_manager.clusters_for_channels)

        # At (or above) the latest generation, load everything (no generation filter)
        gen_filter = None if cutoff >= self.max_generation else cutoff
        self.high_dim_points_for_channels = self.data_loader.load_data_for_channels(gen_filter)
        self.reduced_points_for_reducer = self.reduce_data(self.reducers,
                                                           self.high_dim_points_for_channels)

        # reduce_data refreshes self.channels; re-sync the cluster manager to the new set
        self.cluster_manager.channels = self.channels
        self.clusters_for_channels = {channel: old_clusters.get(channel, 0)
                                      for channel in self.channels}
        self.cluster_manager.clusters_for_channels = self.clusters_for_channels

        self.label_gen_cutoff.setText(self._gen_cutoff_text(cutoff))

        if self.current_reducer is None and self.reducers:
            self.current_reducer = self.reducers[0]
        if self.current_reducer is not None:
            self.plot(self.current_reducer)

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
            # Project the channel's reduced point onto the two components shown.
            point = (data[self.x_axis_idx], data[self.y_axis_idx])
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

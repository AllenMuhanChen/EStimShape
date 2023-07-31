import numpy as np
from PyQt5.QtGui import QColor, QPixmap, QIcon
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QListWidget, QListWidgetItem, \
    QGridLayout
from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.widgets import LassoSelector

MAX_GROUPS = 10


class ApplicationWindow(QWidget):
    def __init__(self, data_loader, data_exporter, pca_reducer, mds_reducer):
        super().__init__()

        self.reduced_data_for_reducer = None
        self.current_reducer = None
        self.data_loader = data_loader
        self.data_exporter = data_exporter
        self.pca_reducer = pca_reducer
        self.mds_reducer = mds_reducer

        self.reduced_data_for_reducer = {}
        self.data_for_channels = self.data_loader.load_data()

        # Create a list of the data for each channel, ensuring each is a 2D array
        data_list = list(self.data_for_channels.values())
        # Concatenate all the data into a single 2D array
        all_data = np.vstack(data_list)
        for reducer in [self.pca_reducer, self.mds_reducer]:
            # Perform dimensionality reduction on all data
            all_reduced_data = reducer.fit_transform(all_data)

            # Split the reduced data back up into channels
            reduced_data_for_channels = {}
            start_index = 0
            for channel_index, channel in enumerate(self.data_for_channels.keys()):
                # Extract the part of all_reduced_data that corresponds to this channel
                reduced_data = all_reduced_data[channel_index, :]
                reduced_data_for_channels[channel] = reduced_data


            self.reduced_data_for_reducer[reducer] = reduced_data_for_channels

        # self.layout = QHBoxLayout(self)
        self.color_map = cm.get_cmap('tab10', MAX_GROUPS)

        # Left side: group list and buttons
        self.group_list = QListWidget()
        # self.layout.addWidget(self.group_list)
        self.group_list.itemClicked.connect(self.on_group_selected)

        self.new_group_button = QPushButton('New Group')
        self.new_group_button.clicked.connect(self.new_group)
        # self.layout.addWidget(self.new_group_button)

        self.delete_group_button = QPushButton('Delete Group')
        self.delete_group_button.clicked.connect(self.delete_group)
        # self.layout.addWidget(self.delete_group_button)

        group_panel = QVBoxLayout()
        group_panel.addWidget(self.new_group_button)
        group_panel.addWidget(self.delete_group_button)
        group_panel.addWidget(self.group_list)

        # TOP PANEL
        # Add PCA button
        self.button_pca = QPushButton('PCA', self)
        self.button_pca.clicked.connect(self.on_pca)  # connect button click to function
        # self.layout.addWidget(self.button_pca)

        # Add MDS button
        self.button_mds = QPushButton('MDS', self)
        self.button_mds.clicked.connect(self.on_mds)  # connect button click to function
        # self.layout.addWidget(self.button_mds)

        top_button_panel = QHBoxLayout()
        top_button_panel.addWidget(self.button_pca)
        top_button_panel.addWidget(self.button_mds)

        # Right side: plot
        # Add matplotlib FigureCanvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # Create the export button and put it in a separate panel
        export_button = QPushButton('Export')
        export_button.clicked.connect(self.on_export)
        export_panel = QVBoxLayout()
        export_panel.addWidget(export_button)

        # Create a grid layout and add all panels
        layout = QGridLayout()
        layout.addLayout(top_button_panel, 0, 0, 1, 2)  # Span 2 columns
        layout.addWidget(self.canvas, 1, 0)  # Below top_button_panel
        layout.addLayout(group_panel, 1, 1)  # To the right of the canvas
        layout.addLayout(export_panel, 2, 1)  # Below group_panel

        # Set stretch factors
        layout.setColumnStretch(0, 3)  # Set stretch factor for column 0 (canvas column) to 3
        layout.setColumnStretch(1, 1)  # Set stretch factor for column 1 (group_panel column) to 1

        self.setLayout(layout)

        # Lasso selection
        self.lasso = None
        self.current_group = 1  # The group that will be assigned to the next selection
        self.num_groups = 2
        self.groups_for_channels = None  # An array that stores the group number of each point

    def on_pca(self):
        # Run PCA and plot the result
        self.plot(self.pca_reducer)
        self.current_reducer = self.pca_reducer

    def on_mds(self):
        # Run MDS and plot the result
        self.plot(self.mds_reducer)
        self.current_reducer = self.mds_reducer

    def plot(self, reducer):
        # Reset groups if the reducer has changed
        if self.current_reducer != reducer:
            self.groups_for_channels = None
            self.current_group = 1

        if self.groups_for_channels is None:
            # Initialize the groups array the first time plot() is called
            self.groups_for_channels = {channel: 0 for channel in self.data_for_channels.keys()}

        # Create a list to store colors for all data points
        point_colors = []
        for channel, data in self.data_for_channels.items():
            group = self.groups_for_channels[channel]
            # For each data point in the current channel, assign the color corresponding to its group
            point_colors.append(self.get_float_color_for_group(group))

        # Plot the reduced data
        self.figure.clear()
        ax = self.figure.subplots()

        # Concatenate the reduced data arrays along the first axis
        reduced_data_values = np.vstack(list(self.reduced_data_for_reducer[reducer].values()))

        # Scatter plot
        ax.scatter(reduced_data_values[:, 0], reduced_data_values[:, 1], c=point_colors, cmap=self.color_map)
        self.canvas.draw()

        # Add lasso selection
        if self.lasso is not None:
            self.lasso.disconnect_events()
        self.lasso = CustomLassoSelector(ax, self.on_lasso_select)

        self.draw_group_list()

    def get_qcolor_for_group(self, i):
        color = self.get_float_color_for_group(i)
        color = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))  # Convert to QColor
        return color

    def get_float_color_for_group(self, i):
        color = self.color_map(i / MAX_GROUPS)  # Calculate the color of this group
        return color

    def new_group(self):
        # Increment current_group, but don't assign it to any points yet
        self.current_group += 1
        self.num_groups += 1
        self.draw_group_list()

    def draw_group_list(self):
        self.group_list.clear()
        # self.group_list.addItem('Group {}'.format(self.current_group))
        for i in range(self.num_groups):
            color = self.get_qcolor_for_group(i)
            pixmap = QPixmap(20, 20)
            pixmap.fill(color)
            icon = QIcon(pixmap)
            item = QListWidgetItem(icon, 'Group {}'.format(i))
            self.group_list.addItem(item)

    def delete_group(self):
        # Remove the current group from the groups array and the group list
        current_row = self.group_list.currentRow()
        self.group_list.takeItem(current_row)
        self.groups_for_channels[self.groups_for_channels == current_row] = 0
        self.current_group -= 1
        self.num_groups -= 1
        # Decrement the group numbers of all higher-numbered groups
        for i in range(current_row + 1, self.current_group + 1):
            self.groups_for_channels[self.groups_for_channels == i] = i - 1
        self.draw_group_list()
        self.plot(self.current_reducer)

    def on_lasso_select(self, verts):
        path = Path(verts)
        selected_channels = []

        for channel, data in self.reduced_data_for_reducer[self.current_reducer].items():
            point = data  # since each channel corresponds to one point
            if path.contains_point(point):
                selected_channels.append(channel)

        # Check the mouse button used for lasso selection
        if self.lasso.button == 1:  # Left-click
            # Add selected points to the current group
            for channel in selected_channels:
                self.groups_for_channels[channel] = self.current_group
        elif self.lasso.button == 3:  # Right-click
            # Remove selected points from the current group
            for channel in selected_channels:
                if self.groups_for_channels[channel] == self.current_group:
                    self.groups_for_channels[channel] = 0

        self.plot(self.current_reducer)

    def on_group_selected(self, item):
        # Set the current group to the selected group
        self.current_group = self.group_list.row(item)

    def on_export(self):
        channels_for_clusters = {}
        for channel, group in self.groups_for_channels.items():
            channels_for_clusters[group] = channels_for_clusters.get(group, []) + [channel]
        self.data_exporter.export_data(channels_for_clusters)


class CustomLassoSelector(LassoSelector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button = None

    def press(self, event):
        self.button = event.button
        super().press(event)

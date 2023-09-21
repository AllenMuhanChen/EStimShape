import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox, QPushButton
from pyqtgraph import PlotWidget, PlotDataItem

from intan.channels import Channel
from windowsort.threshold import threshold_spikes


class ThresholdedSpikePlot(QWidget):
    def __init__(self, data_handler, data_exporter):
        super(ThresholdedSpikePlot, self).__init__()
        self.data_handler = data_handler
        self.data_exporter = data_exporter
        self.spike_window_radius_in_indices = 50

        self.min_max_voltage = None
        self.crossing_indices = None
        self.current_threshold_value = None
        self.current_start_index = 0
        self.current_max_spikes = 50  # Default value
        self.initUI()
        self.plotItems = []  # List to keep track of PlotDataItems
        self.current_channel = Channel.C_000

    def initUI(self):
        layout = QVBoxLayout()

        self.plotWidget = PlotWidget()
        layout.addWidget(self.plotWidget)

        self.setLayout(layout)

    def updatePlot(self):
        # Clear the existing plot items
        for item in self.plotItems:
            self.plotWidget.removeItem(item)
        self.plotItems.clear()

        if self.current_threshold_value is None:
            return  # Exit if the threshold is not set yet
        threshold_value = self.current_threshold_value

        voltages = self.data_handler.voltages_by_channel[self.current_channel]

        self.crossing_indices = threshold_spikes(threshold_value, voltages)

        # Calculate the min_max voltage if it is not set yet
        if self.min_max_voltage is None:
            self.min_max_voltage = self.calculate_min_max(voltages, self.spike_window_radius_in_indices)

        # SAVE DATA
        self.data_exporter.update_thresholded_spikes(self.current_channel, self.crossing_indices)

        # PLOT SUBSET OF DATA
        subset_of_crossing_indices = self.crossing_indices[
                                     self.current_start_index:self.current_start_index + self.current_max_spikes]
        for point in subset_of_crossing_indices:
            start = max(0, point - self.spike_window_radius_in_indices)
            end = min(len(voltages), point + self.spike_window_radius_in_indices)
            self.plot_spike(start, end, voltages)

        # Set the y-limits of the plot
        self.set_y_axis_limits()

    def set_y_axis_limits(self):
        if self.min_max_voltage[0] != np.inf and self.min_max_voltage[1] != -np.inf:
            self.plotWidget.setYRange(self.min_max_voltage[0], self.min_max_voltage[1])

    def plot_spike(self, start, end, voltage, color='r'):
        plotItem = PlotDataItem(voltage[start:end], pen=color)
        self.plotWidget.addItem(plotItem)
        self.plotItems.append(plotItem)

    def on_channel_changed(self):
        self.min_max_voltage = None  # Reset the min_max voltage

    def calculate_min_max(self, voltages, window_radius_in_indices):
        min_spike_voltage = np.inf
        max_spike_voltage = -np.inf
        for point in self.crossing_indices:
            start = max(0, point - window_radius_in_indices)
            end = min(len(voltages), point + window_radius_in_indices)
            # Update min and max voltage if necessary
            min_spike_voltage = min(min_spike_voltage, np.min(voltages[start:end]))
            max_spike_voltage = max(max_spike_voltage, np.max(voltages[start:end]))
        return min_spike_voltage, max_spike_voltage


class SpikeScrubber(QWidget):
    def __init__(self, thresholdedSpikePlot):
        super(SpikeScrubber, self).__init__()
        self.thresholdedSpikePlot = thresholdedSpikePlot
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        hbox = QHBoxLayout()

        self.label = QLabel("Index Start:")
        self.slider = QSlider(Qt.Horizontal)
        self.total_spikes_label = QLabel("Total Spikes: 0")  # Initialize with 0

        self.maxSpikesBox = QSpinBox()
        self.maxSpikesBox.setSuffix(" spikes")
        self.maxSpikesBox.setValue(50)  # Initial value
        self.maxSpikesBox.setRange(1, 200)  # Adjust as needed

        hbox.addWidget(self.label)
        hbox.addWidget(self.slider)
        hbox.addWidget(self.total_spikes_label)
        hbox.addWidget(QLabel("Max To Display:"))
        hbox.addWidget(self.maxSpikesBox)

        layout.addLayout(hbox)
        self.setLayout(layout)

        self.slider.valueChanged.connect(self.updateSpikePlot)
        self.maxSpikesBox.valueChanged.connect(self.updateSpikePlot)

    def updateSpikePlot(self):
        self.thresholdedSpikePlot.current_start_index = self.slider.value()
        self.thresholdedSpikePlot.current_max_spikes_to_display = self.maxSpikesBox.value()
        self.thresholdedSpikePlot.updatePlot()

        # Update the total number of spikes
        total_spikes = len(self.thresholdedSpikePlot.crossing_indices)  # Assuming crossing_indices is a numpy array
        self.total_spikes_label.setText(f"Total Spikes: {total_spikes}")


class ExportPanel(QWidget):
    def __init__(self, data_exporter):
        super(ExportPanel, self).__init__()
        self.data_exporter = data_exporter
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.exportButton = QPushButton("Export Data")
        self.exportButton.clicked.connect(self.onExportClicked)

        layout.addWidget(self.exportButton)
        self.setLayout(layout)

    def onExportClicked(self):
        self.data_exporter.export_data()

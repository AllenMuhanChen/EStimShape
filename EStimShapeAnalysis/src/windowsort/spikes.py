import time

import numpy as np
from PyQt5 import sip
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox, QPushButton, QAbstractSlider
from pyqtgraph import PlotWidget, PlotDataItem

from clat.intan.channels import Channel

from windowsort.threshold import threshold_spikes_absolute


class ThresholdedSpikePlot(QWidget):
    def __init__(self, data_handler, data_exporter, default_max_spikes=50):
        super(ThresholdedSpikePlot, self).__init__()
        self.data_handler = data_handler
        self.data_exporter = data_exporter
        self.spike_window_radius_in_indices = 25

        self.min_max_voltage = None
        self.crossing_indices = None
        self.current_threshold_value = None
        self.current_start_index = 0
        self.current_max_spikes = default_max_spikes  # Default value
        self._init_ui()
        self.plotItems = []  # List to keep track of PlotDataItems
        self.current_channel = Channel.C_000

    def updatePlot(self):
        # Clear the existing plot items
        self.clear_plot()

        if self.current_threshold_value is None:
            return  # Exit if the threshold is not set yet
        threshold_value = self.current_threshold_value

        # self.threshold_spikes(threshold_value)

        voltages = self.data_handler.voltages_by_channel[self.current_channel]

        # Calculate the min_max voltage if it is not set yet
        if self.min_max_voltage is None:
            self.min_max_voltage = self._calculate_min_max(voltages, self.spike_window_radius_in_indices)

        # SAVE DATA
        self.data_exporter.update_thresholded_spikes(self.current_channel, self.crossing_indices)

        # PLOT SUBSET OF DATA
        subset_of_crossing_indices = self.crossing_indices[
                                     self.current_start_index:self.current_start_index + self.current_max_spikes]
        for point in subset_of_crossing_indices:
            start = max(0, point - self.spike_window_radius_in_indices)
            end = min(len(voltages), point + self.spike_window_radius_in_indices)
            middle = point
            self._plot_spike(start, end, middle, voltages)

    def threshold_spikes(self, threshold_value):
        self.current_threshold_value = threshold_value
        voltages = self.data_handler.voltages_by_channel[self.current_channel]
        self.crossing_indices = threshold_spikes_absolute(threshold_value, voltages)

    def clear_plot(self):
        for item in self.plotItems:
            self.plotWidget.removeItem(item)
            sip.delete(item)  # delete from C++ memory
        self.plotItems.clear()

    def on_channel_changed(self):
        self.min_max_voltage = None  # Reset the min_max voltage

    def _init_ui(self):
        layout = QVBoxLayout()

        self.plotWidget = PlotWidget()
        layout.addWidget(self.plotWidget)

        self.setLayout(layout)

    def _plot_spike(self, start, end, middle, voltages, color='r'):
        x_axis = np.arange(start, end)
        x_axis = x_axis - middle  # Center the spike
        plotItem = PlotDataItem(x_axis, voltages[start:end], pen=color)
        self.plotWidget.addItem(plotItem)
        self.plotItems.append(plotItem)

    def _calculate_min_max(self, voltages, window_radius_in_indices):
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
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, thresholdedSpikePlot, default_max_spikes: int = 50, slider=None):
        super(SpikeScrubber, self).__init__()
        self.spike_plot = thresholdedSpikePlot
        self.current_max_spikes = 50
        self.page_multiplier = 5
        if slider == None:
            self.slider = QSlider(Qt.Horizontal)
        else:
            self.slider = slider
        self._init_ui()

    def updateValue(self, value):
        self.slider.setValue(value)
        self.slider.valueChanged.emit(value)

    def _init_ui(self):
        layout = QVBoxLayout()
        hbox = QHBoxLayout()

        self.label = QLabel("Index Start:")

        self.total_spikes_label = QLabel("Total Spikes: 0")  # Initialize with 0

        self.maxSpikesBox = QSpinBox()
        self.maxSpikesBox.setSuffix(" spikes")

        self.maxSpikesBox.setValue(self.current_max_spikes)  # Initial value
        self.maxSpikesBox.setRange(1, 300)  # Adjust as needed

        hbox.addWidget(self.label)
        hbox.addWidget(self.slider)
        hbox.addWidget(self.total_spikes_label)
        hbox.addWidget(QLabel("Max To Display:"))
        hbox.addWidget(self.maxSpikesBox)

        layout.addLayout(hbox)
        self.setLayout(layout)

        self.slider.valueChanged.connect(self._update_spike_plot)
        self.slider.setSingleStep(self.current_max_spikes)  # Set single step size
        self.slider.setPageStep(self.current_max_spikes * self.page_multiplier)  # Set page step size
        self.maxSpikesBox.editingFinished.connect(self._update_max_spikes)

    def _update_spike_plot(self):
        rounded_value = (self.slider.value() // self.current_max_spikes) * self.current_max_spikes
        self.slider.setValue(rounded_value)  # This will set the slider to the rounded value

        self.spike_plot.current_start_index = self.slider.value()
        self.currentIndexChanged.emit(self.slider.value())

        # This weird double updatePlot is a temp workaround a glitch
        # Where scrubbing through spikes after you've changed or added a lot of windows
        # causes crazy lag.
        self.spike_plot.current_max_spikes = 0
        self.spike_plot.updatePlot()
        self.spike_plot.current_max_spikes = self.current_max_spikes  # Reset the current max spikes
        self.spike_plot.updatePlot()
        #

        # Update the total number of spikes
        if self.spike_plot.crossing_indices is None:
            self.total_spikes = 0
        else:
            self.total_spikes = len(self.spike_plot.crossing_indices)  # Assuming crossing_indices is a numpy array
            self.slider.setMaximum(self.total_spikes)
            # self.maxSpikesBox.setMaximum(self.total_spikes)

        self.total_spikes_label.setText(f"Total Spikes: {self.total_spikes}")

    def _update_max_spikes(self):
        self.current_max_spikes = self.maxSpikesBox.value()
        self.slider.setSingleStep(self.current_max_spikes)
        self.slider.setPageStep(self.current_max_spikes * self.page_multiplier)
        self._update_spike_plot()


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
        self.data_exporter.save_thresholded_spikes()

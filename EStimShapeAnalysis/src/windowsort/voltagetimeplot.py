from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSlider, QSpinBox, QPushButton
import numpy as np
from pyqtgraph import PlotWidget, PlotDataItem, LinearRegionItem, InfiniteLine

from intan.channels import Channel
from windowsort.datahandler import DataExporter


class VoltageTimePlot(QWidget):
    def __init__(self, data_handler):
        super(VoltageTimePlot, self).__init__()
        self.max_voltage = None
        self.min_voltage = None
        self.data_handler = data_handler
        self.initUI()

        # Add threshold line
        self.threshold_line = InfiniteLine(angle=0, movable=True, pos=-80)
        self.plotWidget.addItem(self.threshold_line)
        self.threshold_line.sigDragged.connect(self.onThresholdChanged)

    def initUI(self):
        layout = QVBoxLayout()

        # Create the main plot
        self.plotWidget = PlotWidget()
        self.plot = self.plotWidget.plot()
        layout.addWidget(self.plotWidget)

        # Add scrub bar (LinearRegionItem) below the main plot
        self.scrubRegion = LinearRegionItem()
        self.scrubRegion.setZValue(10)
        self.plotWidget.addItem(self.scrubRegion)

        self.setLayout(layout)

        # Initialize the plot with data
        self.updatePlot()

    def updatePlot(self, start_time_seconds=0, window_size_seconds=100):
        channel_name = list(self.data_handler.voltages_by_channel.keys())[0]
        voltages = self.data_handler.voltages_by_channel[channel_name]
        sample_rate = self.data_handler.sample_rate

        # Calculate the indices for the time window
        start_index = int(start_time_seconds * sample_rate)
        end_index = int((start_time_seconds + window_size_seconds) * sample_rate)

        # Extract the subset of data for the time window
        voltages_subset = voltages[start_index:end_index]
        times_subset = np.linspace(start_time_seconds, start_time_seconds + window_size_seconds / 1000,
                                   len(voltages_subset))

        # Update the main plot
        self.plot.setData(times_subset, voltages_subset)

        # Update the axes limits to fit the plotted data
        self.plotWidget.setXRange(min(times_subset), max(times_subset))

        if self.min_voltage is None or self.max_voltage is None:
            self.min_voltage = min(voltages)
            self.max_voltage = max(voltages)

        self.plotWidget.setYRange(self.min_voltage, self.max_voltage)

    def onThresholdChanged(self):
        threshold_value = self.threshold_line.value()
        self.thresholdedSpikePlot.current_threshold_value = threshold_value
        self.thresholdedSpikePlot.updatePlotWithSettings()  # Assume start_time and max_spikes are available
    # Additional methods for zooming, setting threshold, etc., can be added


class TimeScrubber(QWidget):
    def __init__(self, voltage_time_plot):
        super(TimeScrubber, self).__init__()
        self.voltage_time_plot = voltage_time_plot
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        hbox = QHBoxLayout()

        self.label = QLabel("Time Window Start:")
        self.slider = QSlider(Qt.Horizontal)

        self.windowSizeBox = QSpinBox()
        self.windowSizeBox.setSuffix(" s")
        self.windowSizeBox.setValue(50)  # Set initial window size to 100 s
        self.windowSizeBox.setRange(1, 1000)

        hbox.addWidget(self.label)
        hbox.addWidget(self.slider)
        hbox.addWidget(QLabel("Window Size:"))
        hbox.addWidget(self.windowSizeBox)

        layout.addLayout(hbox)
        self.setLayout(layout)

        # Get total time duration based on the first channel in the dataset
        channel_name = list(self.voltage_time_plot.data_handler.voltages_by_channel.keys())[0]
        total_samples = len(self.voltage_time_plot.data_handler.voltages_by_channel[channel_name])
        total_time_seconds = (total_samples / self.voltage_time_plot.data_handler.sample_rate)

        self.slider.setRange(0, int(total_time_seconds))  # Set range based on actual data
        self.slider.setValue(0)  # Set initial position

        self.slider.valueChanged.connect(self.updateMainPlot)
        self.windowSizeBox.valueChanged.connect(self.updateMainPlot)

    def updateMainPlot(self):
        start_time = self.slider.value()
        window_size = self.windowSizeBox.value()
        self.voltage_time_plot.updatePlot(start_time, window_size)


class ThresholdedSpikePlot(QWidget):
    def __init__(self, data_handler, data_exporter):
        super(ThresholdedSpikePlot, self).__init__()
        self.data_handler = data_handler
        self.data_exporter = data_exporter
        self.current_threshold_value = None
        self.current_start_time = 0
        self.current_max_spikes = 10  # Default value
        self.initUI()
        self.plotItems = []  # List to keep track of PlotDataItems
        self.current_channel = Channel.C_000

    def initUI(self):
        layout = QVBoxLayout()

        self.plotWidget = PlotWidget()
        layout.addWidget(self.plotWidget)

        self.setLayout(layout)


    def updatePlotWithSettings(self):
        # Clear the existing plot items
        for item in self.plotItems:
            self.plotWidget.removeItem(item)
        self.plotItems.clear()

        threshold_value = self.current_threshold_value


        voltages = self.data_handler.voltages_by_channel[self.current_channel]

        # Find spikes that cross the threshold
        above_threshold = voltages < threshold_value
        crossing_indices = np.where(np.diff(above_threshold))[0]
        self.data_exporter.update_thresholded_spikes(self.current_channel, crossing_indices)
        subset_of_crossing_indices = crossing_indices[self.current_start_time:self.current_start_time + self.current_max_spikes]

        # Plot a small window around each crossing point
        window_size = 50  # For example, 50 samples on either side of the spike
        for point in subset_of_crossing_indices:
            start = max(0, point - window_size)
            end = min(len(voltages), point + window_size)
            plotItem = PlotDataItem(voltages[start:end], pen='r')
            self.plotWidget.addItem(plotItem)
            self.plotItems.append(plotItem)  # Add to list


class SpikeScrubber(QWidget):
    def __init__(self, thresholdedSpikePlot):
        super(SpikeScrubber, self).__init__()
        self.thresholdedSpikePlot = thresholdedSpikePlot
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        hbox = QHBoxLayout()

        self.label = QLabel("Time Start:")
        self.slider = QSlider(Qt.Horizontal)

        self.maxSpikesBox = QSpinBox()
        self.maxSpikesBox.setSuffix(" spikes")
        self.maxSpikesBox.setValue(10)  # Initial value
        self.maxSpikesBox.setRange(1, 100)  # Adjust as needed

        hbox.addWidget(self.label)
        hbox.addWidget(self.slider)
        hbox.addWidget(QLabel("Max Spikes:"))
        hbox.addWidget(self.maxSpikesBox)

        layout.addLayout(hbox)
        self.setLayout(layout)

        self.slider.valueChanged.connect(self.updateSpikePlot)
        self.maxSpikesBox.valueChanged.connect(self.updateSpikePlot)

    def updateSpikePlot(self):
        self.thresholdedSpikePlot.current_start_time = self.slider.value()
        self.thresholdedSpikePlot.current_max_spikes = self.maxSpikesBox.value()
        self.thresholdedSpikePlot.updatePlotWithSettings()



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

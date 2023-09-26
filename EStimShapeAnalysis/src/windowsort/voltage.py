from PyQt5.QtWidgets import QHBoxLayout, QComboBox
import numpy as np
from pyqtgraph import PlotWidget, LinearRegionItem, InfiniteLine

from intan.channels import Channel
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSlider, QSpinBox, QLabel

from windowsort.spikes import ThresholdedSpikePlot


class VoltageTimePlot(QWidget):
    current_channel: Channel = None
    spike_plot: ThresholdedSpikePlot = None

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

        self.setLayout(layout)

        # Initialize the plot with data
        self.updatePlot()

    def updatePlot(self, start_time_seconds=0, window_size_seconds=100):
        if self.current_channel is None:
            return
        channel_name = self.current_channel
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
        self.spike_plot.threshold_spikes(threshold_value)
        self.spike_plot.updatePlot()  # Assume start_time and max_spikes are available
    # Additional methods for zooming, setting threshold, etc., can be added


class ThresholdControlPanel(QWidget):
    def __init__(self, voltage_time_plot):
        super(ThresholdControlPanel, self).__init__()
        self.voltage_time_plot = voltage_time_plot
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.thresholdLabel = QLabel("Threshold Value:")
        layout.addWidget(self.thresholdLabel)

        # Initialize Slider
        self.thresholdSlider = QSlider(Qt.Horizontal)
        self.thresholdSlider.setRange(-200, 200)  # Set your own range
        self.thresholdSlider.setValue(-80)  # Initial value
        layout.addWidget(self.thresholdSlider)

        # Initialize SpinBox
        self.thresholdSpinBox = QSpinBox()
        self.thresholdSpinBox.setRange(-200, 200)  # Set your own range
        self.thresholdSpinBox.setValue(-80)  # Initial value
        layout.addWidget(self.thresholdSpinBox)

        self.setLayout(layout)

        # Connect Slider and SpinBox to update together
        self.thresholdSlider.valueChanged.connect(self.thresholdSpinBox.setValue)
        self.thresholdSpinBox.editingFinished.connect(self.thresholdSlider.setValue)

        # Connect to update the threshold line in VoltageTimePlot
        self.thresholdSlider.valueChanged.connect(self.updateThresholdLine)
        self.thresholdSpinBox.editingFinished.connect(self.updateThresholdLine)

    def updateThresholdLine(self):
        new_threshold_value = self.thresholdSlider.value()
        self.voltage_time_plot.threshold_line.setValue(new_threshold_value)
        self.voltage_time_plot.onThresholdChanged()


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


class ChannelSelectionPanel(QWidget):
    def __init__(self, voltage_time_plot, thresholded_spike_plot):
        super(ChannelSelectionPanel, self).__init__()
        self.voltage_time_plot = voltage_time_plot
        self.thresholded_spike_plot = thresholded_spike_plot
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.channelComboBox = QComboBox()
        channel_list = list(self.voltage_time_plot.data_handler.voltages_by_channel.keys())
        self.channelComboBox.addItems([channel.value for channel in channel_list])

        layout.addWidget(QLabel("Select Channel:"))
        layout.addWidget(self.channelComboBox)

        self.setLayout(layout)

        self.channelComboBox.currentIndexChanged.connect(self.onChannelChanged)

    def onChannelChanged(self):
        selected_channel = Channel(self.channelComboBox.currentText())
        print("Selected channel: " + selected_channel.value)
        self.voltage_time_plot.current_channel = selected_channel
        self.thresholded_spike_plot.current_channel = selected_channel
        self.voltage_time_plot.updatePlot()

        self.thresholded_spike_plot.updatePlot()
        self.thresholded_spike_plot.on_channel_changed()

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSlider, QSpinBox
import numpy as np
from pyqtgraph import PlotWidget, PlotDataItem, LinearRegionItem

class VoltageTimePlot(QWidget):
    def __init__(self, data_handler):
        super(VoltageTimePlot, self).__init__()
        self.data_handler = data_handler
        self.initUI()

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

    def updatePlot(self, start_time=0, window_size=100):
        channel_name = list(self.data_handler.voltages_by_channel.keys())[0]
        voltages = self.data_handler.voltages_by_channel[channel_name]
        sample_rate = self.data_handler.sample_rate

        # Calculate the indices for the time window
        start_index = int(start_time * sample_rate)
        end_index = int((start_time + window_size / 1000) * sample_rate)

        # Extract the subset of data for the time window
        voltages_subset = voltages[start_index:end_index]
        times_subset = np.linspace(start_time, start_time + window_size / 1000, len(voltages_subset))

        # Update the main plot
        self.plot.setData(times_subset, voltages_subset)

        # Update the axes limits to fit the plotted data
        self.plotWidget.setXRange(min(times_subset), max(times_subset))
        self.plotWidget.setYRange(min(voltages_subset), max(voltages_subset))
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
        self.windowSizeBox.setSuffix(" ms")
        self.windowSizeBox.setValue(100)  # Set initial window size to 100 ms

        hbox.addWidget(self.label)
        hbox.addWidget(self.slider)
        hbox.addWidget(QLabel("Window Size:"))
        hbox.addWidget(self.windowSizeBox)

        layout.addLayout(hbox)
        self.setLayout(layout)

        self.slider.setRange(0, 100)  # Set actual range based on data
        self.slider.valueChanged.connect(self.updateMainPlot)
        self.windowSizeBox.valueChanged.connect(self.updateMainPlot)

    def updateMainPlot(self):
        start_time = self.slider.value() / 1000  # Convert from ms to seconds
        window_size = self.windowSizeBox.value()  # In ms
        self.voltage_time_plot.updatePlot(start_time, window_size)

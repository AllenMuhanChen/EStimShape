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
        self.current_threshold_value = None
        self.current_start_index = 0
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

        if self.current_threshold_value is None:
            return  # Exit if the threshold is not set yet
        threshold_value = self.current_threshold_value

        voltages = self.data_handler.voltages_by_channel[self.current_channel]

        crossing_indices = threshold_spikes(threshold_value, voltages)

        # SAVE DATA
        self.data_exporter.update_thresholded_spikes(self.current_channel, crossing_indices)

        # PLOT SUBSET OF DATA
        subset_of_crossing_indices = crossing_indices[
                                     self.current_start_index:self.current_start_index + self.current_max_spikes]

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
        self.maxSpikesBox.setValue(50)  # Initial value
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
        self.thresholdedSpikePlot.current_start_index = self.slider.value()
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

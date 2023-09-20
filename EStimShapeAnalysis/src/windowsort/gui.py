from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
import sys
import os

from windowsort.datahandler import DataImporter, DataExporter
from windowsort.voltagetimeplot import VoltageTimePlot, TimeScrubber, ThresholdedSpikePlot, SpikeScrubber, ExportPanel, \
    ChannelSelectionPanel


class MainWindow(QMainWindow):
    def __init__(self, data_directory):
        super(MainWindow, self).__init__()

        # Initialize Dependencies
        self.data_handler = DataImporter(data_directory)
        self.data_exporter = DataExporter(save_directory=data_directory)

        # Initialize UI
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Voltage Trace GUI")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # Voltage Time Plot
        self.voltage_time_plot = VoltageTimePlot(self.data_handler)
        layout.addWidget(self.voltage_time_plot)
        self.time_scrubber = TimeScrubber(self.voltage_time_plot)
        layout.addWidget(self.time_scrubber)


        # Thresholded Spikes
        self.thresholded_spike_plot = ThresholdedSpikePlot(self.data_handler, self.data_exporter)
        layout.addWidget(self.thresholded_spike_plot)
        self.voltage_time_plot.thresholdedSpikePlot = self.thresholded_spike_plot
        self.spike_scrubber = SpikeScrubber(self.thresholded_spike_plot)
        layout.addWidget(self.spike_scrubber)

        # Exporting
        self.exportPanel = ExportPanel(self.data_exporter)
        layout.addWidget(self.exportPanel)
        layout.addWidget(self.exportPanel)

        # Channel Selection
        self.channel_selection_pannel = ChannelSelectionPanel(self.voltage_time_plot, self.thresholded_spike_plot)
        layout.insertWidget(0, self.channel_selection_pannel)  # Inserts at the top of the layout

        central_widget.setLayout(layout)


# Main function to run the application
def main():
    app = QApplication(sys.argv)

    # Define the data directory here
    date = "2023-09-12"
    exp_name = "1694529683452000_230912_144921"
    data_directory = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/%s/%s/" % (
    date, exp_name)

    mainWin = MainWindow(data_directory)
    mainWin.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

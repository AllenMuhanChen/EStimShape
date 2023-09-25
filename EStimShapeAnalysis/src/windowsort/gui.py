from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication, QHBoxLayout
import sys
import os

from windowsort.datahandler import DataImporter, DataExporter
from windowsort.timeampwindow import SortSpikePlot, SortPanel
from windowsort.voltage import VoltageTimePlot, TimeScrubber, ChannelSelectionPanel, ThresholdControlPanel
from windowsort.spikes import ThresholdedSpikePlot, SpikeScrubber, ExportPanel


class MainWindow(QMainWindow):
    def __init__(self, data_directory):
        super(MainWindow, self).__init__()

        # Initialize Dependencies
        self.data_handler = DataImporter(data_directory)
        self.data_exporter = DataExporter(save_directory=data_directory)

        # Initialize UI
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Time Amp Window Sort GUI")

        central_widget = QWidget()
        main_layout = QHBoxLayout()

        # FIRST COLUMN
        self.setCentralWidget(central_widget)

        # Two Columns
        threshold_layout = QVBoxLayout()
        spike_plot_layout = QVBoxLayout()
        spike_sort_layout = QVBoxLayout()

        # Voltage Time Plot
        self.voltage_time_plot = VoltageTimePlot(self.data_handler)
        threshold_layout.addWidget(self.voltage_time_plot)
        self.time_scrubber = TimeScrubber(self.voltage_time_plot)
        threshold_layout.addWidget(self.time_scrubber)
        self.threshold_control_panel = ThresholdControlPanel(self.voltage_time_plot)
        threshold_layout.addWidget(self.threshold_control_panel)

        # Thresholded Spikes
        self.spike_plot = SortSpikePlot(self.data_handler, self.data_exporter)
        spike_plot_layout.addWidget(self.spike_plot)
        self.voltage_time_plot.spike_plot = self.spike_plot
        self.spike_scrubber = SpikeScrubber(self.spike_plot)
        spike_plot_layout.addWidget(self.spike_scrubber)

        # Exporting
        self.exportPanel = ExportPanel(self.data_exporter)
        threshold_layout.addWidget(self.exportPanel)
        threshold_layout.addWidget(self.exportPanel)

        # Channel Selection
        self.channel_selection_pannel = ChannelSelectionPanel(self.voltage_time_plot, self.spike_plot)
        threshold_layout.insertWidget(0, self.channel_selection_pannel)  # Inserts at the top of the layout

        # Logical Rules
        spike_sort_panel = SortPanel(self.spike_plot, self.data_exporter)
        spike_sort_layout.insertWidget(0, spike_sort_panel)
        self.spike_plot.set_sort_panel(spike_sort_panel)
        # Add more Time-Amp related widgets to spike_sort_layout if needed

        # Add the second column layout to the main layout
        main_layout.addLayout(threshold_layout)
        main_layout.addLayout(spike_plot_layout)
        main_layout.addLayout(spike_sort_layout)

        central_widget.setLayout(main_layout)



# Main function to run the application
def main():
    app = QApplication(sys.argv)

    # Define the data directory here
    date = "2023-09-12"
    exp_name = "1694529683452000_230912_144921"
    # exp_name = "1694801146439198_230915_140547"
    data_directory = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/%s/%s/" % (
    date, exp_name)

    print("Loading App")

    mainWin = MainWindow(data_directory)
    mainWin.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

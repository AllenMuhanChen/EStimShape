from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
import sys
import os

from windowsort.datahandler import DataHandler
from windowsort.voltagetimeplot import VoltageTimePlot, TimeScrubber


class MainWindow(QMainWindow):
    def __init__(self, data_directory):
        super(MainWindow, self).__init__()

        # Initialize DataHandler
        self.data_handler = DataHandler(data_directory)

        # Initialize UI
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Voltage Trace GUI")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        self.voltage_time_plot = VoltageTimePlot(self.data_handler)
        layout.addWidget(self.voltage_time_plot)

        self.time_scrubber = TimeScrubber(self.voltage_time_plot)
        layout.addWidget(self.time_scrubber)

        central_widget.setLayout(layout)


# Main function to run the application
def main():
    app = QApplication(sys.argv)

    # Define the data directory here
    data_directory = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/2023-09-15/1694801146439198_230915_140547/"

    mainWin = MainWindow(data_directory)
    mainWin.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

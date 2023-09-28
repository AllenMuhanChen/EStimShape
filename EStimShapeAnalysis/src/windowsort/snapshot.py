import random

import numpy as np
from PyQt5.QtWidgets import QCheckBox, QSlider, QLabel, QLineEdit, QPushButton
from pyqtgraph import PlotDataItem

from windowsort.spikes import ThresholdedSpikePlot
from windowsort.units import Unit, SortPanel


class SnapshotPlot(ThresholdedSpikePlot):
    def __init__(self, data_handler, data_exporter, sort_panel: SortPanel, default_max_spikes=50):
        super(SnapshotPlot, self).__init__(data_handler, data_exporter, default_max_spikes=default_max_spikes)

        # Reference to SortPanel for accessing sort_all_spikes method and units
        self.sort_panel = sort_panel

        self.unit_visibility = {}
        self.unit_checkboxes = []

        # Additional UI elements for SnapshotPlot
        self.initSnapshotUI()

    def initSnapshotUI(self):

        # Placeholder for unit visibility controls
        self.updateUnitControl()

        # Create an 'Update Plot' button
        self.update_plot_button = QPushButton('Update Plot')
        self.update_plot_button.clicked.connect(self.updateSnapshotPlot)
        self.layout().addWidget(self.update_plot_button)

        # Placeholder for max spikes control as a QLineEdit (textbox)
        self.max_spikes_textbox = QLineEdit()
        self.max_spikes_textbox.editingFinished.connect(self.set_max_spikes)
        self.layout().addWidget(QLabel("Max Spikes:"))
        self.layout().addWidget(self.max_spikes_textbox)

    def updateUnitControl(self):
        # Remove old checkboxes from the layout if they exist
        for checkbox in self.unit_checkboxes:
            self.layout().removeWidget(checkbox)
            checkbox.deleteLater()

        self.unit_checkboxes = []
        self.units = self.sort_panel.spike_plot.units
        for unit in self.units:  # Fetch units from SortPanel
            checkbox = QCheckBox(unit.unit_name)
            checkbox.setChecked(True)
            # Set the checkbox to its previous state if applicable
            if unit.unit_name in self.unit_visibility:
                checkbox.setChecked(self.unit_visibility[unit.unit_name])
            checkbox.stateChanged.connect(self.toggle_unit_visibility)

            self.layout().addWidget(checkbox)
            self.unit_checkboxes.append(checkbox)

    def updateSnapshotPlot(self):
        self.updateUnitControl()
        self.update_unit_visibility()
        print("Updating Snapshot Plot")
        # Fetch sorted spikes using sort_all_spikes from SortPanel
        channel = self.sort_panel.spike_plot.current_channel
        sorted_spikes = self.sort_panel.sort_all_spikes(channel)
        print(sorted_spikes)
        # Clear the existing plot
        self.clear_plot()

        # Loop through sorted spikes and plot them
        for unit in self.units:
            unit_name = unit.unit_name
            spikes = sorted_spikes[unit_name]
            if self.unit_is_visible(unit_name):  # Check if this unit is supposed to be visible
                self.plot_spikes_for_unit(unit, spikes)

    import random

    def plot_spikes_for_unit(self, unit, spike_indices):
        # Fetch the color for this unit; could be dynamically assigned or fetched from the unit object
        color = unit.color

        # Fetch the voltages for the current channel
        channel = self.sort_panel.spike_plot.current_channel
        voltages = self.data_handler.voltages_by_channel[channel]

        # Check if the number of spikes exceeds max_spikes, and if so, sample randomly
        if len(spike_indices) > self.current_max_spikes:
            spike_indices = random.sample(spike_indices, self.current_max_spikes)

        # Loop through each spike index and plot the corresponding voltage trace
        for spike_index in spike_indices:
            start = max(0, spike_index - self.spike_window_radius_in_indices)
            end = min(len(voltages), spike_index + self.spike_window_radius_in_indices)
            middle = spike_index

            # Define your x_axis values here; this can be time or index-based
            x_axis = np.arange(start, end) - middle  # Centering the spike

            # Create and add a PlotDataItem
            plot_item = PlotDataItem(x_axis, voltages[start:end], pen=color)
            self.plotWidget.addItem(plot_item)

            # Keep track of PlotDataItems if necessary
            self.plotItems.append(plot_item)

    def toggle_unit_visibility(self):
        self.update_unit_visibility()

        # Update the plot based on new visibility settings
        self.updateSnapshotPlot()

    def update_unit_visibility(self):
        # Loop through checkboxes to find which units should be visible
        for checkbox in self.unit_checkboxes:
            unit_name = checkbox.text()
            if checkbox.isChecked():
                self.set_unit_visible(unit_name)
            else:
                self.set_unit_hidden(unit_name)

    def set_max_spikes(self):
        # Get the current max_spikes value from the textbox
        try:
            max_spikes = int(self.max_spikes_textbox.text())
        except ValueError:
            print("Invalid input. Please enter a number.")
            return

        # Update the internal state to reflect this new max_spikes value
        self.current_max_spikes = max_spikes  # or some other appropriate action

        # Update the plot to reflect this new max_spikes value
        self.updateSnapshotPlot()

    def unit_is_visible(self, unit_name):
        return self.unit_visibility.get(unit_name, False)

    def set_unit_visible(self, unit_name):
        self.unit_visibility[unit_name] = True

    def set_unit_hidden(self, unit_name):
        self.unit_visibility[unit_name] = False
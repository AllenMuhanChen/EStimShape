from __future__ import annotations

import itertools
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox

from windowsort.threshold import threshold_spikes_absolute


class Unit:
    def __init__(self, logical_expression, unit_name, color):
        self.logical_expression = logical_expression  # Expression can be something like "W1 and not W2"
        self.unit_name = unit_name  # Unit identifier, e.g., "Unit 1"
        self.color = color  # Color for the unit, e.g., 'green'

    def sort_spike(self, *, index_of_spike, voltages, amp_time_windows):
        # If there's only one window, return its result directly
        if len(amp_time_windows) == 1:
            return amp_time_windows[0].is_spike_in_window(index_of_spike, voltages)

        # Otherwise, evaluate the logical expression
        window_results = {}
        for idx, window in enumerate(amp_time_windows):
            window_results[f'w{idx + 1}'] = window.is_spike_in_window(index_of_spike, voltages)

        # Convert the expression to lowercase to make it Python-compatible
        python_compatible_expression = self.logical_expression.lower()
        python_compatible_expression = self.upper_case_true_false(python_compatible_expression)
        python_compatible_expression = self.process_ignore_operators(python_compatible_expression)

        try:
            result = eval(python_compatible_expression, {}, window_results)
        except:
            result = False
            print("Invalid expression: ", python_compatible_expression)
        return result

    @staticmethod
    def upper_case_true_false(expression: str) -> str:
        processed_expression = expression
        # Find all occurrences of "True" and replace with "True"
        if "true" in processed_expression:
            processed_expression = processed_expression.replace("true", "True")

        # Find all occurrences of "False" and replace with "False"
        if "false" in processed_expression:
            processed_expression = processed_expression.replace("false", "False")

        return processed_expression

    @staticmethod
    def process_ignore_operators(expression: str) -> str:
        processed_expression = expression
        # Find all occurrences of "IGNORE Wx" and replace with "True AND"
        for i in range(1, 10):  # Assuming up to W9 for this example
            ignore_str = f"ignore w{i}"
            if ignore_str in processed_expression:
                processed_expression = processed_expression.replace(ignore_str, "and True")

        return processed_expression


def unit_color_generator():
    colors = ['pink', 'yellow', 'orange']
    return itertools.cycle(colors)


def create_wrapped_label(unit_name_label):
    wrapper = QWidget()
    wrapper_layout = QVBoxLayout()
    wrapper_layout.addWidget(unit_name_label, alignment=Qt.AlignCenter)
    wrapper.setLayout(wrapper_layout)
    return wrapper


class DropdownUnitPanel:
    """
    subpanel within SortPanel that controls a single unit
    """

    def __init__(self, unit_counter, unit_color, parent_layout, thresholded_spike_plot, delete_func):
        self.states_by_dropdown_index = {}
        self.unit = None
        self.unit_counter = unit_counter
        self.unit_color = unit_color
        self.parent_layout = parent_layout
        self.delete_func = delete_func
        self.spike_plot = thresholded_spike_plot
        self.dropdowns = []
        self.expression = None

    def populate(self):
        self.unit_layout = QHBoxLayout()

        self.add_delete_button()

        self.add_unit_label()

        self.create_unit()
        self.populate_unit_dropboxes()
        self.parent_layout.addLayout(self.unit_layout)

    def add_unit_label(self):
        # Add unit name and set the background color
        label = QLabel(f"Unit {self.unit_counter}")
        label.setStyleSheet(f"background-color: {self.unit_color};")
        # Contain the label within a wrapper
        wrapper = create_wrapped_label(label)
        # Add the wrapper to the unit layout
        self.unit_layout.addWidget(wrapper)

    def add_delete_button(self):
        # Add a Delete button
        delete_button = QPushButton("Delete Unit")
        delete_button.clicked.connect(lambda: self.delete_func(self))
        self.unit_layout.addWidget(delete_button)

    def cache_dropdown_states(self):
        for dropdown_index, dropdown in enumerate(self.dropdowns):
            self.states_by_dropdown_index[dropdown_index] = dropdown.currentIndex()

    def restore_dropdown_states(self):
        try:
            for dropdown_index, choice_index in self.states_by_dropdown_index.items():
                self.dropdowns[dropdown_index].setCurrentIndex(choice_index)
        except Exception:
            pass

    def populate_unit_dropboxes(self):
        if self.unit_layout is None:
            print("Warning: Attempting to populate a layout that no longer exists.")
            return

        #

        # Store current dropdown states
        window_colors = self.spike_plot.get_window_colors()
        window_color_iterator = itertools.cycle(window_colors)
        num_windows = len(self.spike_plot.amp_time_windows)

        # Populate the unit layouts with dropdowns and labels
        if num_windows > 0:
            first_window_dropdown = QComboBox()
            first_window_dropdown.addItems(["INCLUDE", "IGNORE", "NOT"])
            self.unit_layout.addWidget(first_window_dropdown)
            first_window_dropdown.currentIndexChanged.connect(self.update_expression)  # Connect the signal
            self.dropdowns.append(first_window_dropdown)

            # Add the label for the first window
            first_window_label = QLabel("W1")
            first_window_label.setStyleSheet(f"background-color: {next(window_color_iterator)};")
            self.unit_layout.addWidget(create_wrapped_label(first_window_label))

            for i, window in enumerate(self.spike_plot.amp_time_windows[1:]):
                dropdown = QComboBox()
                dropdown.addItems(["AND", "OR", "AND NOT", "IGNORE"])
                dropdown.currentIndexChanged.connect(self.update_expression)  # Connect the signal
                self.unit_layout.addWidget(dropdown)
                self.dropdowns.append(dropdown)

                # Add the label for this window
                window_label = QLabel(f"W{i + 2}")
                window_label.setStyleSheet(f"background-color: {next(window_color_iterator)};")
                self.unit_layout.addWidget(create_wrapped_label(window_label))

            # Restore dropdown states if any exist
            self.restore_dropdown_states()

        self.update_expression()

    def create_unit(self):
        self.expression = self.generate_expression(self.dropdowns)
        self.unit = Unit(self.expression, f"Unit {self.unit_counter}", self.unit_color)
        self.spike_plot.addUnit(self.unit)

    def generate_expression(self, dropdowns):
        if not dropdowns:  # Check if the list is empty
            return ""
        expression_parts = []
        first_operator = dropdowns[0].currentText()
        if first_operator == "INCLUDE":
            expression_parts.append(f"W1")
        elif first_operator == "IGNORE":
            expression_parts.append(f"True")
        elif first_operator == "NOT":
            expression_parts.append(f"not W1")

        for i, dropdown in enumerate(dropdowns[1:]):
            operator = dropdown.currentText()
            expression_parts.append(f"{operator} W{i + 2}")

        return ' '.join(expression_parts)

    def update_expression(self):
        """Update the logical expression based on the current dropdown selections."""
        if not self.dropdowns:  # Check if the list is empty
            return
        self.cache_dropdown_states()
        self.expression = self.generate_expression(self.dropdowns)
        updated_unit = Unit(self.expression, f"Unit {self.unit_counter}", self.unit_color)
        self.spike_plot.updateUnit(updated_unit)
        self.spike_plot.sortSpikes()  # Evaluate the rules for all spikes

    def clear_unit_layout(self):
        try:
            """Clear existing widgets and dropdowns from the unit layout."""
            for i in reversed(range(self.unit_layout.count())):
                widget = self.unit_layout.itemAt(i).widget()
                if widget is not None:
                    widget.deleteLater()

            self.dropdowns.clear()
        except RuntimeError:
            pass


class SortPanel(QWidget):
    unit_panels: List[DropdownUnitPanel]

    def __init__(self, thresholded_spike_plot, data_exporter):
        super(SortPanel, self).__init__(thresholded_spike_plot)
        self.spike_plot = thresholded_spike_plot
        self.data_exporter = data_exporter
        self.unit_panels = []
        self.unit_counter = 0  # to generate unique unit identifiers
        self.current_color = None
        self.unit_colors = unit_color_generator()  # to generate unique colors for units
        self.layout = QVBoxLayout()

        # Add a button for adding new units
        self.add_unit_button = QPushButton("Add New Unit")
        self.add_unit_button.clicked.connect(self.add_new_unit)
        self.layout.addWidget(self.add_unit_button)

        # Add Export button
        self.export_button = QPushButton("Export Sorted Spikes")
        self.export_button.clicked.connect(self.export_sorted_spikes)
        self.layout.addWidget(self.export_button)

        self.setLayout(self.layout)

    def emit_recalculate_windows(self):
        self.spike_plot.windowUpdated.emit()

    def add_new_unit(self):
        self.unit_counter += 1
        self.current_color = next(self.unit_colors)
        new_unit_panel = DropdownUnitPanel(self.unit_counter, self.current_color, self.layout, self.spike_plot,
                                           self.delete_unit)
        new_unit_panel.populate()
        self.unit_panels.append(new_unit_panel)

    def generate_expression(self, dropdowns):
        expression_parts = []

        # Handle the first dropdown separately (YES or NO)
        first_operator = dropdowns[0].currentText()
        if first_operator == "INCLUDE":
            expression_parts.append(f"W1")
        elif first_operator == "IGNORE":
            expression_parts.append(f"True")
        elif first_operator == "NOT":
            expression_parts.append(f"not W1")

        # Handle the rest of the dropdowns
        for i, dropdown in enumerate(dropdowns[1:]):
            operator = dropdown.currentText()
            expression_parts.append(f"{operator} W{i + 2}")

        # Add the last window
        # if len(dropdowns) > 0:
        #     expression_parts.append(f"W{len(dropdowns)}")

        return ' '.join(expression_parts)

    def update_panels(self):
        """Update dropdowns in each unit layout to match the current number of windows."""
        # Clear each unit layout and rebuild it
        for unit_panel in self.unit_panels:
            unit_panel.clear_unit_layout()  # Clear the existing widgets and dropdowns
            unit_panel.add_unit_label()
            unit_panel.add_delete_button()
            unit_panel.populate_unit_dropboxes()  # Repopulate the widgets and dropdowns

    def get_window_colors(self):
        window_colors = [window.color for window in self.spike_plot.amp_time_windows]
        return window_colors

    def delete_unit(self, unit_panel):
        """Delete a specific unit."""
        # Remove unit from the list
        self.unit_panels.remove(unit_panel)

        # Actually remove the unit from data
        self.spike_plot.removeUnit(unit_panel.unit.unit_name)

        # Clear and delete layout
        unit_panel.clear_unit_layout()
        del unit_panel

        # Repopulate remaining units
        self.update_panels()

        self.spike_plot.sortSpikes()

    def export_sorted_spikes(self):
        channel = self.spike_plot.current_channel
        voltages = self.spike_plot.data_handler.voltages_by_channel[channel]

        self.spike_plot.updatePlot()  # Make sure the data is updated

        sorted_spikes_by_unit = {}

        # Pre-compute the crossing indices for the current channel
        threshold_value = self.spike_plot.current_threshold_value
        crossing_indices = threshold_spikes_absolute(threshold_value, voltages)

        for unit in self.spike_plot.units:
            sorted_spikes = []  # List to hold the sorted spikes for this unit

            for point in crossing_indices:
                spike_index = round(point)  # or however you wish to define this

                # Check if the spike belongs to the current unit
                if unit.sort_spike(index_of_spike=spike_index, voltages=voltages,
                                   amp_time_windows=self.spike_plot.amp_time_windows):
                    sorted_spikes.append(spike_index)

            sorted_spikes_by_unit[unit.unit_name] = sorted_spikes

        # Use the DataExporter to save the sorted spikes
        self.data_exporter.save_sorted_spikes(sorted_spikes_by_unit, channel)

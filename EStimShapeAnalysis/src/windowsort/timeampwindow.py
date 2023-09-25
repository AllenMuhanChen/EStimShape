from __future__ import annotations

import itertools
import math
from typing import List

from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, pyqtSignal, QTimer, QVariant
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtWidgets import QVBoxLayout, QGraphicsEllipseItem, QGraphicsItem, QWidget, QPushButton, QHBoxLayout, QLabel, \
    QComboBox
from pyqtgraph import InfiniteLine, PlotDataItem, PlotWidget

from windowsort.spikes import ThresholdedSpikePlot

from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem

from windowsort.threshold import threshold_spikes_absolute


class AmpTimeWindow(QGraphicsItem):
    def __init__(self, x, y, height, color, parent=None, parent_plot=None):
        super(AmpTimeWindow, self).__init__(parent)
        self.parent_plot = parent_plot
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        self.window_update_timer = QTimer()
        self.window_update_timer.setSingleShot(True)
        self.window_update_timer.timeout.connect(self.emit_window_updated)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

        self.height = height  # Height of the line
        self.color = color  # Color of the line
        self.setZValue(1)

        # The values we will compare voltages of spikes to in order to sort them
        self.sort_ymax = None
        self.sort_ymin = None
        self.sort_x = None

        # Correct the initial position so that the line is centered on the mouse
        y = (y / 2)
        # Set the initial position in scene coordinates
        self.setPos(x, y)
        self.calculate_x_y_for_sorting()

    def calculate_x_y_for_sorting(self):
        self.sort_x = self.pos().x() * 2
        self.sort_ymin = self.pos().y() * 2 - self.height / 2
        self.sort_ymax = self.pos().y() * 2 + self.height / 2

    def paint(self, painter, option, widget=None):
        """For some reason the drawn x and y locations are ALWAYS a factor of 2 off from
        the x and y location our mouse is on the plot. I have no idea why.

        To correct for this, we take the drawn locations and multiply by two to correct for this. """
        y_min = self.pos().y() - self.height / 2
        y_max = self.pos().y() + self.height / 2
        self.pen = QPen(QColor(self.color))
        self.pen.setWidthF(0.25)
        painter.setPen(self.pen)
        painter.drawLine(QPointF(self.pos().x(), y_min), QPointF(self.pos().x(), y_max))

        self.calculate_x_y_for_sorting()

    def boundingRect(self):
        y_center = (self.y_min() + self.y_max()) / 2
        y_range = self.y_max() - self.y_min()
        y_margin = y_range * 0.5  # 25% towards the center from each control point

        new_y_min = y_center - y_margin
        new_y_max = y_center + y_margin

        return QRectF(self.pos().x() - 1, new_y_min, 2, new_y_max - new_y_min)

    def y_min(self):
        return self.pos().y() - self.height / 2

    def y_max(self):
        return self.pos().y() + self.height / 2

    def emit_window_updated(self):
        self.parent_plot.windowUpdated.emit()

    def is_spike_in_window(self, index_of_spike, voltages):
        offset_index = int(self.sort_x)

        # Calculate the index in the voltage array to check
        check_index = index_of_spike + offset_index

        # Make sure the index is within bounds
        if 0 <= check_index < len(voltages):
            voltage_to_check = voltages[check_index]
            return self.sort_ymin <= voltage_to_check <= self.sort_ymax
        else:
            return False

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_x = int(
                value.x()) / 2.0  # lock it to ints and divide by 2 to allow for moving one integer at a time (because of weird scaling)
            new_y = value.y()  # Keep the y-coordinate as is

            if not self.window_update_timer.isActive():
                self.window_update_timer.start(100)  # emit_window_updated will be called after 100 ms

            return QPointF(new_x, new_y)
        return super(AmpTimeWindow, self).itemChange(change, value)

    def keyPressEvent(self, event):
        if self.isSelected():
            if event.key() == Qt.Key_Up:
                self.height += 1  # Increase height when the Up arrow key is pressed
            elif event.key() == Qt.Key_Down:
                self.height = max(1,
                                  self.height - 1)  # Decrease height when the Down arrow key is pressed, with a minimum limit
            # Redraw the item to reflect the new height
            self.update()
            # Emit the signal to update the plot
            self.emit_window_updated()


class CustomPlotWidget(PlotWidget):
    def __init__(self, parent=None):
        super(CustomPlotWidget, self).__init__(parent)
        self.parent = parent

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier:
            print("event pos: " + str(event.pos()))
            pos = self.plotItem.vb.mapSceneToView(event.pos())
            aspect_ratio = self.plotItem.vb.width() / self.plotItem.vb.height()
            self.parent.addAmpTimeWindow(pos.x(), pos.y(), 40)
        super(CustomPlotWidget, self).mousePressEvent(event)


class SortSpikePlot(ThresholdedSpikePlot):
    windowUpdated = pyqtSignal()
    units: List[Unit]
    amp_time_windows: List[AmpTimeWindow]

    def __init__(self, data_handler, data_exporter, default_max_spikes=50):
        super(SortSpikePlot, self).__init__(data_handler, data_exporter, default_max_spikes=default_max_spikes)
        self.logical_rules_panel = None
        self.units = []
        self.amp_time_windows = []
        self.next_color = color_generator()
        self.windowUpdated.connect(self.sortSpikes)

    def initUI(self):
        layout = QVBoxLayout()
        self.plotWidget = CustomPlotWidget(self)
        # self.plotWidget.getPlotItem().setAspectLocked(True)  # Lock the aspect ratio
        layout.addWidget(self.plotWidget)
        self.setLayout(layout)

    def addAmpTimeWindow(self, x, y, height):
        color = next(self.next_color)
        new_window = AmpTimeWindow(x, y, height, color, parent_plot=self)
        self.amp_time_windows.append(new_window)
        self.plotWidget.addItem(new_window)
        self.logical_rules_panel.update_unit_dropdowns()  # Update the dropdowns
        self.windowUpdated.emit()
        self.sortSpikes()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            for window in self.amp_time_windows:
                if window.isSelected():
                    self.plotWidget.removeItem(window)
                    self.amp_time_windows.remove(window)
                    break  # Assuming only one item can be selected at a time
        elif event.key() in (Qt.Key_Up, Qt.Key_Down):
            for window in self.amp_time_windows:
                if window.isSelected():
                    if event.key() == Qt.Key_Up:
                        window.height += 5  # Increase height when the Up arrow key is pressed
                    elif event.key() == Qt.Key_Down:
                        window.height = max(5,
                                            window.height - 5)  # Decrease height when the Down arrow key is pressed, with a minimum limit
                    # Redraw the item to reflect the new height
                    window.update()
                    # Emit the signal to update the plot
                    window.emit_window_updated()

    def sort_and_plot_spike(self, start, end, middle, voltages):
        color = 'r'  # default color
        spike_index = round(middle)  # or however you wish to define this

        num_units_matched = 0
        for unit in self.units:
            if unit.sort_spike(index_of_spike=spike_index, voltages=voltages, amp_time_windows=self.amp_time_windows):
                num_units_matched += 1
                color = unit.color

            if num_units_matched > 1:
                print("Warning: more than one unit matched the spike at index " + str(spike_index))
                color = 'white'
        super().plot_spike(start, end, middle, voltages, color)

    def addUnit(self, rule: Unit):
        new_rule = rule
        self.units.append(new_rule)

    def sortSpikes(self):
        try:
            voltages = self.data_handler.voltages_by_channel[self.current_channel]
            subset_of_crossing_indices = self.crossing_indices[
                                         self.current_start_index:self.current_start_index + self.current_max_spikes]

            for point in subset_of_crossing_indices:
                start = max(0, point - self.spike_window_radius_in_indices)
                end = min(len(voltages), point + self.spike_window_radius_in_indices)
                middle = point

                # Here, we'll use the custom plot_spike_with_color method to plot the spike
                self.sort_and_plot_spike(start, end, middle, voltages)
        except TypeError:
            pass

    def updatePlot(self):

        self.clear_plot()

        if self.current_threshold_value is None:
            return  # Exit if the threshold is not set yet

        voltages = self.data_handler.voltages_by_channel[self.current_channel]
        # Calculate the min_max voltage if it is not set yet
        if self.min_max_voltage is None:
            self.min_max_voltage = self.calculate_min_max(voltages, self.spike_window_radius_in_indices)

        self.sortSpikes()

        # Set the y-limits of the plot
        self.set_y_axis_limits()

    def set_sort_panel(self, logical_rules_panel):
        self.logical_rules_panel = logical_rules_panel

    def updateUnit(self, updated_unit: Unit):
        for i, unit in enumerate(self.units):
            if unit.unit_name == updated_unit.unit_name:
                self.units[i] = updated_unit
                return
        print(f"Unit {updated_unit.unit_name} not found.")

    def get_window_colors(self):
        return [window.color for window in self.amp_time_windows]

    def removeUnit(self, unit_name):
        self.units = [unit for unit in self.units if unit.unit_name != unit_name]


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
        except SyntaxError:
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


def color_generator():
    colors = ['green', 'cyan', 'magenta']
    return itertools.cycle(colors)


def unit_color_generator():
    colors = ['pink', 'blue', 'orange']
    return itertools.cycle(colors)


class UnitPanel:
    """
    subpanel within SortPanel that controls a single unit
    """

    def __init__(self, unit_counter, unit_color, parent_layout, thresholded_spike_plot, delete_func):
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

        # Add unit name and set the background color
        label = QLabel(f"Unit {self.unit_counter}")
        label.setStyleSheet(f"background-color: {self.unit_color};")

        # Contain the label within a wrapper
        wrapper = self.create_wrapped_label(label)

        # Add the wrapper to the unit layout
        self.unit_layout.addWidget(wrapper)

        self.create_unit()
        self.populate_unit_dropboxes()
        self.parent_layout.addLayout(self.unit_layout)

    def add_delete_button(self):
        # Add a Delete button
        delete_button = QPushButton("Delete Unit")
        delete_button.clicked.connect(lambda: self.delete_func(self))
        self.unit_layout.addWidget(delete_button)

    def create_wrapped_label(self, unit_name_label):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout()
        wrapper_layout.addWidget(unit_name_label, alignment=Qt.AlignCenter)
        wrapper.setLayout(wrapper_layout)
        return wrapper

    def populate_unit_dropboxes(self):
        if self.unit_layout is None:
            print("Warning: Attempting to populate a layout that no longer exists.")
            return

        window_colors = self.spike_plot.get_window_colors()
        window_color_iterator = itertools.cycle(window_colors)
        num_windows = len(self.spike_plot.amp_time_windows)
        if num_windows > 0:
            first_window_dropdown = QComboBox()
            first_window_dropdown.addItems(["INCLUDE", "IGNORE", "NOT"])
            self.unit_layout.addWidget(first_window_dropdown)
            first_window_dropdown.currentIndexChanged.connect(self.update_expression)  # Connect the signal
            self.dropdowns.append(first_window_dropdown)

            # Add the label for the first window
            first_window_label = QLabel("W1")
            first_window_label.setStyleSheet(f"background-color: {next(window_color_iterator)};")
            self.unit_layout.addWidget(self.create_wrapped_label(first_window_label))

            for i, window in enumerate(self.spike_plot.amp_time_windows[1:]):
                dropdown = QComboBox()
                dropdown.addItems(["AND", "OR", "AND NOT", "IGNORE"])
                dropdown.currentIndexChanged.connect(self.update_expression)  # Connect the signal
                self.unit_layout.addWidget(dropdown)
                self.dropdowns.append(dropdown)

                # Add the label for this window
                window_label = QLabel(f"W{i + 2}")
                window_label.setStyleSheet(f"background-color: {next(window_color_iterator)};")
                self.unit_layout.addWidget(self.create_wrapped_label(window_label))

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
    unit_panels: List[UnitPanel]

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
        new_unit_panel = UnitPanel(self.unit_counter, self.current_color, self.layout, self.spike_plot,
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

    def update_unit_dropdowns(self):
        """Update dropdowns in each unit layout to match the current number of windows."""
        # Clear each unit layout and rebuild it
        for unit_panel in self.unit_panels:
            unit_panel.clear_unit_layout()  # Clear the existing widgets and dropdowns
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
        self.update_unit_dropdowns()

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
from __future__ import annotations

import itertools
from typing import List

from PyQt5 import sip
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QVBoxLayout, QAbstractSlider
from pyqtgraph import PlotWidget

from windowsort.spikes import ThresholdedSpikePlot, SpikeScrubber

from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtWidgets import QGraphicsItem

from windowsort.units import Unit


class TimeAmplitudeWindow(QGraphicsItem):
    def __init__(self, x, y, height, color, parent=None, parent_plot=None):
        super().__init__(parent)
        self.parent_plot = parent_plot
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        # Window Updating
        self.window_update_timer = QTimer()
        self.window_update_timer.setSingleShot(True)
        self.window_update_timer.timeout.connect(self.emit_window_updated)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

        # Drag and Drop Timer
        self.drag_delay = 300
        self.drag_started = False
        self.drag_timer = QTimer()
        self.drag_timer.setSingleShot(True)
        self.drag_timer.timeout.connect(self._start_drag)

        self.height = height  # Height of the line
        self.color = color  # Color of the line
        self.setZValue(1)  # We want this drawing to be on top of everything else

        self.pen = QPen(QColor(self.color))
        self.pen.setWidthF(0.25)

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
        """For some reason the drawn x and y locations are ALWAYS a factor of 2 off from
            the x and y location our mouse is on the plot. I have no idea why.

            To correct for this, we take the drawn locations and multiply by two to correct for this. """

        self.sort_x = self.pos().x() * 2
        self.sort_ymin = self.pos().y() * 2 - self.height / 2
        self.sort_ymax = self.pos().y() * 2 + self.height / 2

    def paint(self, painter, option, widget=None):
        y_min = self.pos().y() - self.height / 2
        y_max = self.pos().y() + self.height / 2

        painter.setPen(self.pen)
        painter.drawLine(QPointF(self.pos().x(), y_min), QPointF(self.pos().x(), y_max))

    def boundingRect(self):
        y_center = (self.y_min() + self.y_max()) / 2
        y_range = self.y_max() - self.y_min()
        y_margin = y_range * 0.5  # 25% towards the center from each control point

        new_y_min = y_center - y_margin
        new_y_max = y_center + y_margin

        return QRectF(self.pos().x() - 0.5, new_y_min, 1, new_y_max - new_y_min)

    def y_min(self):
        return self.pos().y() - self.height / 2

    def y_max(self):
        return self.pos().y() + self.height / 2

    def emit_window_updated(self):
        self.parent_plot.windowUpdated.emit()

    def is_spike_in_window(self, spike_voltage_index, index_of_spike, voltages):
        self.calculate_x_y_for_sorting()

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
            new_x = int(value.x() * 2) / 2
            new_y = value.y()

            if not self.window_update_timer.isActive():
                self.window_update_timer.start(100)  # emit_window_updated will be called after 100 ms

            return QPointF(new_x, new_y)
        return super(TimeAmplitudeWindow, self).itemChange(change, value)

    def keyPressEvent(self, event):
        if self.isSelected():
            if event.key() == Qt.Key_Up:
                self.height += 5  # Increase height when the Up arrow key is pressed
            elif event.key() == Qt.Key_Down:
                self.height = max(1,
                                  self.height - 5)  # Decrease height when the Down arrow key is pressed, with a minimum limit
            # Redraw the item to reflect the new height
            self.update()
            # Emit the signal to update the plot
            self.emit_window_updated()

    def _start_drag(self):
        self.drag_started = True

    def mousePressEvent(self, event):
        self.drag_started = False
        self.drag_timer.start(self.drag_delay)  # 300 ms delay before dragging can start
        super(TimeAmplitudeWindow, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_started:
            super(TimeAmplitudeWindow, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_timer.stop()  # stop the timer if the mouse is released before the drag starts
        self.drag_started = False
        super(TimeAmplitudeWindow, self).mouseReleaseEvent(event)


class CustomPlotWidget(PlotWidget):
    def __init__(self, parent=None):
        super(CustomPlotWidget, self).__init__(parent)
        self.parent = parent

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier:
            pos = self.plotItem.vb.mapSceneToView(event.pos())
            self.parent.add_amp_time_window(round(pos.x()) / 2, pos.y(), 40)
        super(CustomPlotWidget, self).mousePressEvent(event)

    def keyPressEvent(self, event):
        # propagate keypresses to children
        for child in self.plotItem.items:
            child.keyPressEvent(event)


class SortSpikePlot(ThresholdedSpikePlot):
    windowUpdated = pyqtSignal()
    units: List[Unit]
    amp_time_windows: List[TimeAmplitudeWindow]
    spike_scrubber: SpikeScrubber

    def __init__(self, data_handler, data_exporter, default_max_spikes=50):
        super(SortSpikePlot, self).__init__(data_handler, data_exporter, default_max_spikes=default_max_spikes)
        self.logical_rules_panel = None
        self.spike_scrubber = None
        self.units = []
        self.amp_time_windows = []
        self.next_color = window_color_generator()
        self.windowUpdated.connect(self.on_window_adjustments)

    def on_window_adjustments(self):
        """
        Called when the user adjusts the amp time windows. (i.e moving, resizing)
        :return:
        """
        self.sortSpikes()

    def update_unit_panel_expressions(self, deleted_window_number=None):
        """
        Called when the user adds or deletes a window.
        :return:
        """
        self.logical_rules_panel.on_window_number_change(deleted_window_number=deleted_window_number)

    def _init_ui(self):
        layout = QVBoxLayout()
        self.plotWidget = CustomPlotWidget(self)
        # self.plotWidget.getPlotItem().setAspectLocked(True)  # Lock the aspect ratio
        layout.addWidget(self.plotWidget)
        self.setLayout(layout)

    def add_amp_time_window(self, x, y, height):
        color = next(self.next_color)
        new_window = TimeAmplitudeWindow(x, y, height, color, parent_plot=self)

        self.amp_time_windows.append(new_window)
        self.plotWidget.addItem(new_window)
        self.update_unit_panel_expressions()
        self.sortSpikes()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for window_index, window in enumerate(self.amp_time_windows):
                if window.isSelected():
                    self.plotWidget.removeItem(window)
                    self.amp_time_windows.remove(window)
                    self.on_window_adjustments()
                    self.update_unit_panel_expressions(deleted_window_number=window_index + 1)
                    break
        elif event.key() in (Qt.Key_Left, Qt.Key_Right):
            if event.modifiers() & Qt.ShiftModifier:
                if event.key() == Qt.Key_Left:
                    self.spike_scrubber.slider.triggerAction(QAbstractSlider.SliderPageStepSub)

                elif event.key() == Qt.Key_Right:
                    self.spike_scrubber.slider.triggerAction(QAbstractSlider.SliderPageStepAdd)

            else:
                if event.key() == Qt.Key_Left:
                    self.spike_scrubber.slider.triggerAction(QAbstractSlider.SliderSingleStepSub)

                elif event.key() == Qt.Key_Right:
                    self.spike_scrubber.slider.triggerAction(QAbstractSlider.SliderSingleStepAdd)

    def sort_and_plot_spike(self, start, end, middle, voltages, spike_number):
        color = 'r'  # default color
        spike_index_in_voltage = round(middle)  # or however you wish to define this

        num_units_matched = 0
        for unit in self.units:
            if unit.sort_spike(voltage_index_of_spike=spike_index_in_voltage, spike_number=spike_number,
                               voltages=voltages, amp_time_windows=self.amp_time_windows):
                num_units_matched += 1
                color = unit.color

            if num_units_matched > 1:
                print("Warning: more than one unit matched the spike at index " + str(spike_index_in_voltage))
                color = 'white'
        super()._plot_spike(start, end, middle, voltages, color)

    def addUnit(self, rule: Unit):
        new_rule = rule
        self.units.append(new_rule)

    def sortSpikes(self):
        try:
            voltages = self.data_handler.voltages_by_channel[self.current_channel]
            subset_of_crossing_indices = self.crossing_indices[
                                         self.current_start_index:self.current_start_index + self.current_max_spikes]

            for index_of_crossing, point in enumerate(subset_of_crossing_indices):
                start = max(0, point - self.spike_window_radius_in_indices)
                end = min(len(voltages), point + self.spike_window_radius_in_indices)
                middle = point
                start_index = self.current_start_index
                spike_number = index_of_crossing + start_index
                # We have to add the start index to the spike number to get the correct spike number in the entire recording
                self.sort_and_plot_spike(start, end, middle, voltages, spike_number)
        except TypeError:
            pass

    def updatePlot(self):
        self.clear_plot()

        if self.current_threshold_value is None:
            return  # Exit if the threshold is not set yet

        voltages = self.data_handler.voltages_by_channel[self.current_channel]

        # Calculate the min_max voltage if it is not set yet
        if self.min_max_voltage is None:
            self.min_max_voltage = self._calculate_min_max(voltages, self.spike_window_radius_in_indices)

        self.sortSpikes()

    def set_sort_panel(self, logical_rules_panel):
        self.logical_rules_panel = logical_rules_panel

    def updateUnit(self, updated_unit: Unit):
        for i, unit in enumerate(self.units):
            if unit.unit_name == updated_unit.unit_name:
                self.units[i] = updated_unit
                return
        print(self.units)
        print(f"Unit {updated_unit.unit_name} not found.")

    def get_window_colors(self):
        return [window.color for window in self.amp_time_windows]

    def removeUnit(self, unit_name):
        self.units = [unit for unit in self.units if unit.unit_name != unit_name]

    def clear_amp_time_windows(self):
        self.next_color = window_color_generator()
        for window in self.amp_time_windows:
            self.plotWidget.removeItem(window)
            sip.delete(window)

        self.amp_time_windows = []

    def clear_units(self):
        self.units = []  # Assuming this is your list of units


def window_color_generator():
    colors = ['green', 'cyan', 'magenta', 'blue', 'darkGreen', 'darkCyan', 'darkMagenta', 'darkBlue']
    return itertools.cycle(colors)

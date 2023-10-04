from __future__ import annotations
from typing import List

from PyQt5.QtCore import pyqtSlot, QPointF, Qt
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import QGraphicsItem, QSlider

from windowsort.spikes import SpikeScrubber
from windowsort.timeamplitudewindow import TimeAmplitudeWindow, SortSpikePlot


class DriftSpikePlot(SortSpikePlot):
    # Dependencies: set these after construction
    spike_scrubber: SpikeScrubber

    def __init__(self, data_handler, data_exporter, default_max_spikes=50):
        super().__init__(data_handler, data_exporter, default_max_spikes=default_max_spikes)
        self.spike_scrubber = None

    def add_amp_time_window(self, x, y, height):
        color = next(self.next_color)
        new_window = DriftingTimeAmplitudeWindow(x, y, height, color, parent_plot=self,
                                                 spike_scrubber=self.spike_scrubber)

        self.amp_time_windows.append(new_window)
        self.plotWidget.addItem(new_window)
        self.update_dropdowns()
        self.sortSpikes()

    def load_amp_time_window(self, time_control_points):
        color = next(self.next_color)
        new_window = DriftingTimeAmplitudeWindow.create_from_time_control_points(time_control_points, color,
                                                                                 parent_plot=self,
                                                                                 spike_scrubber=self.spike_scrubber)
        self.amp_time_windows.append(new_window)
        self.plotWidget.addItem(new_window)
        self.update_dropdowns()
        self.sortSpikes()


class MarkedSlider(QSlider):
    windows: List[DriftingTimeAmplitudeWindow]

    def __init__(self, spike_plot: DriftSpikePlot, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.spike_plot = spike_plot
        self.marker_width = 2

    def paintEvent(self, e):
        # Let QSlider handle its own painting first
        super(MarkedSlider, self).paintEvent(e)

        self._draw_ticks()

    def mousePressEvent(self, e):
        # Let QSlider handle its own event first
        super(MarkedSlider, self).mousePressEvent(e)

        # Check if left mouse button was pressed
        if e.button() == Qt.LeftButton:
            value = self._pixel_to_value(e.x())
            closest_tick = self.find_closest_tick(value)
            if closest_tick is not None:
                self.setValue(closest_tick)
                self.valueChanged.emit(closest_tick)

    def find_closest_tick(self, value):
        """
        Finds the tick closest to the given value.
        """
        closest_tick = None
        min_dist = float('inf')  # start with "infinity" as the minimum distance

        # Search through all windows and all ticks
        for window in self.windows:
            control_points = window.time_control_points
            tick_locations = list(control_points.keys())

            for tick_location in tick_locations:
                dist = abs(tick_location - value)
                if dist < min_dist:
                    min_dist = dist
                    closest_tick = tick_location

        return closest_tick

    def _draw_ticks(self):
        painter = QPainter(self)
        self.windows = self.spike_plot.amp_time_windows
        for window in self.windows:
            color = window.color
            control_points = window.time_control_points
            tick_locations = list(control_points.keys())

            for tick_location in tick_locations:
                pixel_x = self._value_to_pixel(tick_location)
                painter.setPen(QColor(color))
                width = self.marker_width
                height = 10
                painter.drawRect(int(pixel_x - width / 2), 0, width, height)
        painter.end()

    def _value_to_pixel(self, value):
        # Convert a slider value to a pixel position.
        return int(((value - self.minimum()) / (self.maximum() - self.minimum())) * self.width())

    def _pixel_to_value(self, pixel):
        """
        Convert a pixel position to a slider value.
        """
        return int((pixel / self.width()) * (self.maximum() - self.minimum()) + self.minimum())

class DriftingTimeAmplitudeWindow(TimeAmplitudeWindow):
    current_spike_number: int
    time_control_points: dict

    def __init__(self, x, y, height, color, parent_plot=None, spike_scrubber=None):
        super().__init__(x, y, height, color, parent_plot=parent_plot)
        self.time_control_points = {
            0: {'height': height, 'x': x, 'y': y}  # Default control point at index 0
        }
        self.current_spike_number = 0  # Current index of the time control point

        # If spike_scrubber is provided, connect to it
        self.spike_scrubber = spike_scrubber
        if spike_scrubber:
            self._connect_to_spike_scrubber()

    @staticmethod
    def create_from_time_control_points(time_control_points, color, parent_plot=None, spike_scrubber=None):
        # Create a new DriftingAmpTimeWindow from a dictionary of time_control_points
        first_control_point = time_control_points[0]
        first_x = first_control_point['x']
        first_y = first_control_point['y']
        first_height = first_control_point['height']
        new_window = DriftingTimeAmplitudeWindow(first_x, first_y, first_height, color, parent_plot=parent_plot,
                                                 spike_scrubber=spike_scrubber)
        new_window.time_control_points = time_control_points

        return new_window

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

        dx = 0.5
        dy = 2
        if self.isSelected():
            if event.key() == Qt.Key_Up:
                self.height += 2  # Increase height when the Up arrow key is pressed
            elif event.key() == Qt.Key_Down:
                self.height = max(1,
                                  self.height - 2)  # Decrease height when the Down arrow key is pressed, with a minimum limit
            elif event.key() == Qt.Key_Space:
                # Create a new time_control_point with the current attributes
                self._add_time_control_point()
                print("Added time control point at spike_number {}".format(self.current_spike_number))
            elif event.key() == Qt.Key_Backspace:
                if self.current_spike_number != 0:
                    self._remove_time_control_point()
                # Redraw the item to reflect the new height
            elif event.key() == Qt.Key_W:
                self.moveBy(0, dy)
            elif event.key() == Qt.Key_S:
                self.moveBy(0, -dy)
            elif event.key() == Qt.Key_A:
                self.moveBy(-dx, 0)
            elif event.key() == Qt.Key_D:
                self.moveBy(dx, 0)

            self.update()
            self._update_control_point(self.x(), self.y())
            # Emit the signal to update the plot
            self.emit_window_updated()

    def is_spike_in_window(self, voltage_index_of_spike, spike_number, voltages):
        """

        :param voltage_index_of_spike: in the amplifier.dat data, at what index
        did this spike cross the threshold

        :param spike_number: what number spike is this in the file. chronological order.
        :param voltages:
        :return:
        """
        # convert index_of_spike to ordered index
        time_control_point, index = self._closest_proceeding_time_control(spike_number)

        x = time_control_point['x']
        y = time_control_point['y']
        height = time_control_point['height']

        sort_x = x * 2
        sort_ymin = y * 2 - height / 2
        sort_ymax = y * 2 + height / 2

        offset_index = int(sort_x)

        # Calculate the index in the voltage array to check
        check_index = voltage_index_of_spike + offset_index

        # Make sure the index is within bounds
        if 0 <= check_index < len(voltages):
            voltage_to_check = voltages[check_index]
            return sort_ymin <= voltage_to_check <= sort_ymax
        else:
            return False

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_x = int(value.x() * 2) / 2
            new_y = value.y()

            self._update_control_point(new_x, new_y)

            if not self.window_update_timer.isActive():
                self.window_update_timer.start(100)  # emit_window_updated will be called after 100 ms

            return QPointF(new_x, new_y)
        return super(TimeAmplitudeWindow, self).itemChange(change, value)

    def update_current_spike_number(self, new_spike_number):
        self.current_spike_number = new_spike_number
        self._update_drawing_and_sorting()

    def _update_control_point(self, x, y):
        try:
            closest_time_control_point, spike_number = self._closest_proceeding_time_control(self.current_spike_number)
            # Update the height, x, and y values at the closest time index
            closest_time_control_point[
                'height'] = self.height  # assuming self.height is up-to-date
            closest_time_control_point['x'] = x
            closest_time_control_point['y'] = y
        except AttributeError:
            print("AttributeError: itemChange called before init finished?")
            pass  # itemChange called before init finished?

    def _connect_to_spike_scrubber(self):
        self.spike_scrubber.currentIndexChanged.connect(self.update_current_spike_number)

    def _add_time_control_point(self):
        """Adds a new time control point."""
        new_control_point = {
            'height': self.height,
            'x': self.x(),
            'y': self.y()
        }
        self.time_control_points[self.current_spike_number] = new_control_point
        self._update_drawing_and_sorting()

    def _remove_time_control_point(self):
        """Removes a time control point by its start_index."""
        closest_proceeding_time_control, spike_number = self._closest_proceeding_time_control(self.current_spike_number)
        if closest_proceeding_time_control is not None:
            if spike_number != 0:
                del self.time_control_points[spike_number]
        self._update_drawing_and_sorting()

    def _closest_proceeding_time_control(self, current_spike_number):
        """Finds the closest proceeding time control point for a given time."""
        # Assuming the start_indices in the dictionary are sorted
        for spike_number in sorted(self.time_control_points.keys(), reverse=True):
            if spike_number <= current_spike_number:
                return self.time_control_points[spike_number], spike_number
        return None  # Return None if no proceeding time control point exists

    def _update_drawing_and_sorting(self):
        # Fetch the closest preceding time control point for the current time
        # Assuming you have a way to get the 'current_time'
        closest_point, spike_number = self._closest_proceeding_time_control(self.current_spike_number)

        if closest_point is not None:
            # Update attributes based on the closest_point
            # For example, if closest_point is a dictionary containing 'height' and 'location'
            self.height = closest_point['height']
            self.setPos(closest_point['x'], closest_point['y'])

            # Update attributes for sorting
            self.calculate_x_y_for_sorting()

            # Trigger a re-draw (this calls the paint method)
            self.update()

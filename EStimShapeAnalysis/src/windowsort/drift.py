from PyQt5.QtCore import pyqtSlot, QPointF, Qt
from PyQt5.QtWidgets import QGraphicsItem

from windowsort.spikes import SpikeScrubber
from windowsort.timeamplitudewindow import TimeAmplitudeWindow, SortSpikePlot


class DriftSpikePlot(SortSpikePlot):
    # Dependencies: set these after construction
    spike_scrubber: SpikeScrubber

    def __init__(self, data_handler, data_exporter, default_max_spikes=50):
        super().__init__(data_handler, data_exporter, default_max_spikes=default_max_spikes)
        self.spike_scrubber = None

    def addAmpTimeWindow(self, x, y, height):
        color = next(self.next_color)
        new_window = DriftingTimeAmplitudeWindow(x, y, height, color, parent_plot=self, spike_scrubber=self.spike_scrubber)

        self.amp_time_windows.append(new_window)
        self.plotWidget.addItem(new_window)
        self.update_dropdowns()
        self.sortSpikes()

    def loadAmpTimeWindow(self, time_control_points):
        color = next(self.next_color)
        new_window = DriftingTimeAmplitudeWindow.create_from_time_control_points(time_control_points, color, parent_plot=self,
                                                                                 spike_scrubber=self.spike_scrubber)
        self.amp_time_windows.append(new_window)
        self.plotWidget.addItem(new_window)
        self.update_dropdowns()
        self.sortSpikes()


class DriftingTimeAmplitudeWindow(TimeAmplitudeWindow):
    current_spike_number: int

    def __init__(self, x, y, height, color, parent_plot=None, spike_scrubber=None):
        super().__init__(x, y, height, color, parent_plot=parent_plot)
        self.time_control_points = {
            0: {'height': height, 'x': x, 'y': y}  # Default control point at index 0
        }
        self.current_spike_number = 0  # Current index of the time control point

        # If spike_scrubber is provided, connect to it
        self.spike_scrubber = spike_scrubber
        if spike_scrubber:
            self.connect_to_spike_scrubber()

    @staticmethod
    def create_from_time_control_points(time_control_points, color, parent_plot=None, spike_scrubber=None):
        # Create a new DriftingAmpTimeWindow from a dictionary of time_control_points
        # time_control_points: {index: {'height': height, 'x': x, 'y': y}}
        # parent_plot: the parent plot of the new window
        # spike_scrubber: the spike scrubber to connect to
        # Returns: a new DriftingAmpTimeWindow
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
        if self.isSelected():
            if event.key() == Qt.Key_Space:
                # Create a new time_control_point with the current attributes
                self.add_time_control_point()
                print("Added time control point at spike_number {}".format(self.current_spike_number))
            elif event.key() == Qt.Key_Backspace:
                if self.current_spike_number != 0:
                    self.remove_time_control_point()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_x = int(value.x() * 2) / 2
            new_y = value.y()

            try:
                closest_time_control_point, spike_number = self.closest_proceeding_time_control(self.current_spike_number)
                # Update the height, x, and y values at the closest time index
                closest_time_control_point[
                    'height'] = self.height  # assuming self.height is up-to-date
                closest_time_control_point['x'] = new_x
                closest_time_control_point['y'] = new_y
            except AttributeError:
                print("AttributeError: itemChange called before init finished?")
                pass  # itemChange called before init finished?

            if not self.window_update_timer.isActive():
                self.window_update_timer.start(100)  # emit_window_updated will be called after 100 ms

            return QPointF(new_x, new_y)
        return super(TimeAmplitudeWindow, self).itemChange(change, value)

    def update_current_spike_number(self, new_spike_number):
        self.current_spike_number = new_spike_number
        self.update_drawing_and_sorting()

    def connect_to_spike_scrubber(self):
        self.spike_scrubber.currentIndexChanged.connect(self.update_current_spike_number)

    def add_time_control_point(self):
        """Adds a new time control point."""
        new_control_point = {
            'height': self.height,
            'x': self.x(),
            'y': self.y()
        }
        self.time_control_points[self.current_spike_number] = new_control_point
        self.update_drawing_and_sorting()

    def remove_time_control_point(self):
        """Removes a time control point by its start_index."""
        closest_proceeding_time_control, spike_number = self.closest_proceeding_time_control(self.current_spike_number)
        if closest_proceeding_time_control is not None:
            if spike_number != 0:
                del self.time_control_points[spike_number]
        self.update_drawing_and_sorting()

    def closest_proceeding_time_control(self, current_spike_number):
        """Finds the closest proceeding time control point for a given time."""
        # Assuming the start_indices in the dictionary are sorted
        for spike_number in sorted(self.time_control_points.keys(), reverse=True):
            if spike_number <= current_spike_number:
                return self.time_control_points[spike_number], spike_number
        return None  # Return None if no proceeding time control point exists

    def update_drawing_and_sorting(self):
        # Fetch the closest preceding time control point for the current time
        # Assuming you have a way to get the 'current_time'
        closest_point, spike_number = self.closest_proceeding_time_control(self.current_spike_number)

        if closest_point is not None:
            # Update attributes based on the closest_point
            # For example, if closest_point is a dictionary containing 'height' and 'location'
            self.height = closest_point['height']
            self.setPos(closest_point['x'], closest_point['y'])

            # Update attributes for sorting
            self.calculate_x_y_for_sorting()

            # Trigger a re-draw (this calls the paint method)
            self.update()

    def is_spike_in_window(self, voltage_index_of_spike, spike_number, voltages):
        """

        :param voltage_index_of_spike: in the amplifier.dat data, at what index
        did this spike cross the threshold

        :param spike_number: what number spike is this in the file. chronological order.
        :param voltages:
        :return:
        """
        #convert index_of_spike to ordered index
        time_control_point, index = self.closest_proceeding_time_control(spike_number)

        x = time_control_point['x']
        y = time_control_point['y']
        height = time_control_point['height']

        sort_x = x*2
        sort_ymin = y*2 - height / 2
        sort_ymax = y*2 + height / 2

        offset_index = int(sort_x)

        # Calculate the index in the voltage array to check
        check_index = voltage_index_of_spike + offset_index

        # Make sure the index is within bounds
        if 0 <= check_index < len(voltages):
            voltage_to_check = voltages[check_index]
            return sort_ymin <= voltage_to_check <= sort_ymax
        else:
            return False

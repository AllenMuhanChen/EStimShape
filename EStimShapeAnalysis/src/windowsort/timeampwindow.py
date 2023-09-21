import itertools
import math

from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtWidgets import QVBoxLayout, QGraphicsEllipseItem, QGraphicsItem
from pyqtgraph import InfiniteLine, PlotDataItem, PlotWidget

from windowsort.spikes import ThresholdedSpikePlot

from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem


class ControlPoint(QGraphicsEllipseItem):
    def __init__(self, x, y, aspect_ratio, parent=None):
        self.radius = 0.5
        aspect_ratio = aspect_ratio / math.pi
        scaled_radius_x = self.radius / aspect_ratio
        scaled_radius_y = self.radius * aspect_ratio
        super(ControlPoint, self).__init__(
            QRectF(-scaled_radius_x, -scaled_radius_y, 2 * scaled_radius_x, 2 * scaled_radius_y), parent
        )
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # Set the brush and pen color to be the same as the parent line
        color = QColor(parent.color)
        self.setBrush(color)
        self.setPen(QPen(Qt.transparent))
        self.setPos(x, y)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_pos = value
            new_pos.setX(self.parentItem().x)
            self.parentItem().updateLine()
            return new_pos
        return super(ControlPoint, self).itemChange(change, value)


class AmpTimeWindow(QGraphicsItem):
    def __init__(self, x, y_min, y_max, color, aspect_ratio, parent=None):
        super(AmpTimeWindow, self).__init__(parent)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        self.x = x
        print("x: ", x)
        self.y_min = y_min
        self.y_max = y_max
        self.color = color
        self.control_points = []

        # Create control points (small circles)
        for y in [y_min, y_max]:
            control_point = ControlPoint(self.x, y, aspect_ratio, self)
            control_point.setBrush(QColor(self.color))
            control_point.setPos(self.x, y)
            control_point.setFlag(QGraphicsEllipseItem.ItemIsMovable)
            self.control_points.append(control_point)
            print("y: ", y)

    def is_spike_in_window(self, index_of_spike, voltages):
        offset_index = int(self.x)
        y_min, y_max = self.y_min, self.y_max

        # Calculate the index in the voltage array to check
        check_index = index_of_spike + offset_index

        # Make sure the index is within bounds
        if 0 <= check_index < len(voltages):
            voltage_to_check = voltages[check_index]
            return y_min <= voltage_to_check <= y_max
        else:
            return False

    def paint(self, painter, option, widget=None):
        self.pen = QPen(QColor(self.color))
        self.pen.setWidth(0)
        painter.setPen(self.pen)
        painter.drawLine(QPointF(self.x, self.y_min), QPointF(self.x, self.y_max))

    def boundingRect(self):
        y_center = (self.y_min + self.y_max) / 2
        y_range = self.y_max - self.y_min
        y_margin = y_range * 0.5  # 25% towards the center from each control point

        new_y_min = y_center - y_margin
        new_y_max = y_center + y_margin

        return QRectF(self.x - 1, new_y_min, 2, new_y_max - new_y_min)

    def updateLine(self):
        # Update the line based on the new position of control points
        try:
            self.y_min, self.y_max = self.control_points[0].y(), self.control_points[1].y()
            self.update()  # Redraw
        except IndexError:
            pass

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            dx = value.x() - self.x
            self.x += dx
            for control_point in self.control_points:
                control_point.setPos(control_point.x() + dx, control_point.y())
        return super(AmpTimeWindow, self).itemChange(change, value)


class CustomPlotWidget(PlotWidget):
    def __init__(self, parent=None):
        super(CustomPlotWidget, self).__init__(parent)
        self.parent = parent

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier:
            pos = self.plotItem.vb.mapSceneToView(event.pos())
            aspect_ratio = self.plotItem.vb.width() / self.plotItem.vb.height()
            self.parent.addAmpTimeWindow(pos.x(), pos.y() - 20, pos.y() + 20, aspect_ratio)
        super(CustomPlotWidget, self).mousePressEvent(event)


class ExtendedThresholdedSpikePlot(ThresholdedSpikePlot):
    def __init__(self, data_handler, data_exporter):
        super(ExtendedThresholdedSpikePlot, self).__init__(data_handler, data_exporter)
        self.logical_rules_panel = None
        self.amp_time_windows = []
        self.next_color = color_generator()

    def initUI(self):
        layout = QVBoxLayout()
        self.plotWidget = CustomPlotWidget(self)
        # self.plotWidget.getPlotItem().setAspectLocked(True)  # Lock the aspect ratio
        layout.addWidget(self.plotWidget)
        self.setLayout(layout)

    def addAmpTimeWindow(self, x, y_min, y_max, aspect_ratio):
        color = next(self.next_color)
        new_window = AmpTimeWindow(x, y_min, y_max, color, aspect_ratio)
        self.amp_time_windows.append(new_window)
        self.plotWidget.addItem(new_window)
        self.logical_rules_panel.update_unit_dropdowns()  # Update the dropdowns

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            for window in self.amp_time_windows:
                if window.isSelected():
                    self.plotWidget.removeItem(window)
                    self.amp_time_windows.remove(window)
                    break  # Assuming only one item can be selected at a time

    def plot_spike_with_color(self, start, end, middle, voltages):
        print("Plot_spikes_with_color_called")
        # Determine color based on logical rules
        color = 'r'  # default color
        spike_index = start  # or however you wish to define this
        time = start / self.data_handler.sample_rate  # or however you wish to define this

        for rule in self.logical_rules:
            if rule.evaluate(spike_index, time, self.amp_time_windows):
                color = 'g'  # or some other color based on rule
                break

        super().plot_spike(start, end, middle, voltages, color)

    def addLogicalRule(self, rule_expression):
        new_rule = LogicalRule(rule_expression)
        self.logical_rules.append(new_rule)

    def evaluateRules(self):
        for spike in self.spikes:  # Assuming self.spikes is a list of your spikes
            for rule in self.logical_rules:
                if rule.evaluate(spike, self.amp_time_windows):
                    spike.unit = 'Some Unit'  # Assign a unit to the spike based on the rule

    def updatePlot(self):
        super().updatePlot()  # Call the base class method first
        # Additional code to plot based on amp_time_windows and logical_rules

    def set_logical_rules_panel(self, logical_rules_panel):
        self.logical_rules_panel = logical_rules_panel

# In LogicalRule class
class LogicalRule:
    def __init__(self, expression):
        self.expression = expression  # Expression can now be something like "W1 and not W2"

    def evaluate(self, index_of_spike, voltages, amp_time_windows):
        window_results = {}
        for idx, window in enumerate(amp_time_windows):
            window_results[f'W{idx + 1}'] = window.is_spike_in_window(index_of_spike, voltages)
        return eval(self.expression, {}, window_results)


def color_generator():
    colors = ['green', 'cyan', 'magenta', 'orange', 'pink']
    return itertools.cycle(colors)


from PyQt5.QtWidgets import QComboBox, QPushButton, QVBoxLayout, QWidget, QLabel, QHBoxLayout


class LogicalRulesPanel(QWidget):
    def __init__(self, thresholded_spike_plot):
        super(LogicalRulesPanel, self).__init__(thresholded_spike_plot)
        self.thresholded_spike_plot = thresholded_spike_plot
        self.layout = QVBoxLayout()
        self.units_layouts = []  # Store unit layouts to update later

        self.add_unit_button = QPushButton("Add New Unit")
        self.add_unit_button.clicked.connect(self.add_new_unit)
        self.layout.addWidget(self.add_unit_button)

        self.setLayout(self.layout)

    def add_new_unit(self):
        unit_layout = QHBoxLayout()
        self.populate_unit_layout(unit_layout)
        self.units_layouts.append(unit_layout)  # Store this layout to update later
        self.layout.addLayout(unit_layout)

    def update_unit_dropdowns(self):
        """Update dropdowns in each unit layout to match the current number of windows."""
        # Clear each unit layout and rebuild it
        for unit_layout in self.units_layouts:
            for i in reversed(range(unit_layout.count())):
                widget = unit_layout.itemAt(i).widget()
                if widget is not None:
                    widget.deleteLater()
            self.populate_unit_layout(unit_layout)

    def populate_unit_layout(self, unit_layout):
        unit_label = QLabel("Unit: ")
        unit_layout.addWidget(unit_label)

        num_windows = len(self.thresholded_spike_plot.amp_time_windows)
        if num_windows > 0:
            # Add the first window
            window = self.thresholded_spike_plot.amp_time_windows[0]
            color = window.color
            single_window_label = QLabel(f"W1")
            single_window_label.setStyleSheet(f"background-color: {color};")

            wrapper = QWidget()
            wrapper_layout = QVBoxLayout()
            wrapper_layout.addWidget(single_window_label, alignment=Qt.AlignCenter)
            wrapper.setLayout(wrapper_layout)

            unit_layout.addWidget(wrapper)

            for i, window in enumerate(self.thresholded_spike_plot.amp_time_windows[1:]):
                dropdown = QComboBox()
                dropdown.addItems(["AND", "OR", "NOT"])
                unit_layout.addWidget(dropdown)

                window_label = QLabel(f"W{i + 2}")

                # Set the background color of the label
                color = window.color
                window_label.setStyleSheet(f"background-color: {color};")

                wrapper = QWidget()
                wrapper_layout = QVBoxLayout()
                wrapper_layout.addWidget(window_label, alignment=Qt.AlignCenter)
                wrapper.setLayout(wrapper_layout)

                unit_layout.addWidget(wrapper)




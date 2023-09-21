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
        aspect_ratio = aspect_ratio/math.pi
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
        self.x = x
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


    def paint(self, painter, option, widget=None):
        self.pen = QPen(QColor(self.color))
        self.pen.setWidth(0)
        painter.setPen(self.pen)
        painter.drawLine(QPointF(self.x, self.y_min), QPointF(self.x, self.y_max))

    def boundingRect(self):
        return QRectF(self.x - 10, self.y_min - 10, 20, self.y_max - self.y_min + 20)

    def updateLine(self):
        # Update the line based on the new position of control points
        try:
            self.y_min, self.y_max = self.control_points[0].y(), self.control_points[1].y()
            self.update()  # Redraw
        except IndexError:
            pass


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

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            for window in self.amp_time_windows:
                if window.isSelected():
                    self.plotWidget.removeItem(window)
                    self.amp_time_windows.remove(window)
                    break  # Assuming only one item can be selected at a time

    def addLogicalRule(self, rule_expression):
        new_rule = LogicalRule(rule_expression)
        self.logical_rules.append(new_rule)

    def plot_spike_with_color(self, start, end, voltage):
        # Determine color based on logical rules
        color = 'r'  # default color
        spike_index = start  # or however you wish to define this
        time = start / self.data_handler.sample_rate  # or however you wish to define this

        for rule in self.logical_rules:
            if rule.evaluate(spike_index, time, self.amp_time_windows):
                color = 'g'  # or some other color based on rule
                break

        super().plot_spike(start, end, voltage, color)

    def evaluateRules(self):
        # Logic to evaluate rules on spikes
        # This can be used in updatePlot method
        pass

    def updatePlot(self):
        super().updatePlot()  # Call the base class method first
        # Additional code to plot based on amp_time_windows and logical_rules


def color_generator():
    colors = ['green', 'blue', 'purple', 'orange', 'pink']
    return itertools.cycle(colors)


class LogicalRule:
    def __init__(self, expression):
        self.expression = expression  # A lambda function or other callable

    def evaluate(self, spike_index, time, amp_time_windows):
        # Evaluate the rule for the given spike
        return self.expression(spike_index, time, amp_time_windows)

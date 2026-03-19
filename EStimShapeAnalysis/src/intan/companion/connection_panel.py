"""
Connection Panel
================
Widget for managing TCP connections to the Intan RHX software.
Provides host/port fields for both command and waveform sockets,
connect/disconnect buttons, and status display.
"""

from PyQt5.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor


class StatusIndicator(QLabel):
    """A colored dot + text status indicator."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._connected = False
        self._update_display()

    def set_connected(self, connected: bool):
        self._connected = connected
        self._update_display()

    def _update_display(self):
        color = "#4CAF50" if self._connected else "#F44336"
        status = "Connected" if self._connected else "Disconnected"
        self.setText(f'<span style="color:{color};">●</span> {self._label}: {status}')


class ConnectionPanel(QWidget):
    """
    Panel for configuring and controlling TCP connections.

    Signals:
        connect_requested(cmd_host, cmd_port, wave_host, wave_port)
        disconnect_requested()
    """

    connect_requested = pyqtSignal(str, int, str, int)
    disconnect_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        group = QGroupBox("Intan RHX Connection")
        layout = QGridLayout()

        # Command socket config
        layout.addWidget(QLabel("Command Host:"), 0, 0)
        self.cmd_host = QLineEdit("127.0.0.1")
        self.cmd_host.setMaximumWidth(150)
        layout.addWidget(self.cmd_host, 0, 1)

        layout.addWidget(QLabel("Port:"), 0, 2)
        self.cmd_port = QSpinBox()
        self.cmd_port.setRange(0, 65535)
        self.cmd_port.setValue(5000)
        layout.addWidget(self.cmd_port, 0, 3)

        # Waveform socket config
        layout.addWidget(QLabel("Waveform Host:"), 1, 0)
        self.wave_host = QLineEdit("127.0.0.1")
        self.wave_host.setMaximumWidth(150)
        layout.addWidget(self.wave_host, 1, 1)

        layout.addWidget(QLabel("Port:"), 1, 2)
        self.wave_port = QSpinBox()
        self.wave_port.setRange(0, 65535)
        self.wave_port.setValue(5001)
        layout.addWidget(self.wave_port, 1, 3)

        # Buttons
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect)
        btn_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.disconnect_btn.setEnabled(False)
        btn_layout.addWidget(self.disconnect_btn)

        layout.addLayout(btn_layout, 2, 0, 1, 4)

        # Status indicators
        status_layout = QHBoxLayout()
        self.cmd_status = StatusIndicator("Command")
        self.wave_status = StatusIndicator("Waveform")
        status_layout.addWidget(self.cmd_status)
        status_layout.addWidget(self.wave_status)
        status_layout.addStretch()

        # System info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        status_layout.addWidget(self.info_label)

        layout.addLayout(status_layout, 3, 0, 1, 4)

        group.setLayout(layout)

        outer = QVBoxLayout()
        outer.addWidget(group)
        outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer)

    def _on_connect(self):
        self.connect_requested.emit(
            self.cmd_host.text(), self.cmd_port.value(),
            self.wave_host.text(), self.wave_port.value()
        )

    def _on_disconnect(self):
        self.disconnect_requested.emit()

    def set_connected(self, cmd: bool, wave: bool):
        """Update the UI to reflect connection state."""
        self.cmd_status.set_connected(cmd)
        self.wave_status.set_connected(wave)
        connected = cmd and wave
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.cmd_host.setEnabled(not connected)
        self.cmd_port.setEnabled(not connected)
        self.wave_host.setEnabled(not connected)
        self.wave_port.setEnabled(not connected)

    def set_system_info(self, text: str):
        """Display system info (sample rate, controller type, etc)."""
        self.info_label.setText(text)

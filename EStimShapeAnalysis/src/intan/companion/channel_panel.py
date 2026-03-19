"""
Channel Panel
=============
Displays TCP-enabled channels discovered from the Intan RHX.
Shows channels in the order they'll be plotted (matching channel_order
convention from the existing analysis code).

Users can reorder channels or provide a custom channel_order list
to match their probe geometry.
"""

from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QLineEdit, QAbstractItemView
)
from PyQt5.QtCore import pyqtSignal, Qt

from intan_tcp_client import ChannelInfo


class ChannelPanel(QWidget):
    """
    Panel displaying discovered TCP-enabled channels.

    The channel order here determines plotting order (top-to-bottom = shallow-to-deep),
    matching the channel_order convention in LFPSpectrumPlotter, LFPBandPowerPlotter, etc.

    Signals:
        channel_order_changed(list_of_channel_names)
        scan_requested()
    """

    channel_order_changed = pyqtSignal(list)
    scan_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels: List[ChannelInfo] = []
        self._setup_ui()

    def _setup_ui(self):
        group = QGroupBox("TCP-Enabled Channels")
        layout = QVBoxLayout()

        # Scan button
        top_row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Channels")
        self.scan_btn.clicked.connect(self.scan_requested.emit)
        self.scan_btn.setEnabled(False)
        top_row.addWidget(self.scan_btn)

        self.count_label = QLabel("No channels found")
        self.count_label.setStyleSheet("color: #888;")
        top_row.addWidget(self.count_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Channel list (supports drag reorder)
        self.channel_list = QListWidget()
        self.channel_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.channel_list.setMaximumHeight(200)
        self.channel_list.model().rowsMoved.connect(self._on_order_changed)
        layout.addWidget(self.channel_list)

        # Custom order input
        order_row = QHBoxLayout()
        order_row.addWidget(QLabel("Channel order:"))
        self.order_input = QLineEdit()
        self.order_input.setPlaceholderText("e.g. 0,1,2,3,4,5 (blank = as discovered)")
        order_row.addWidget(self.order_input)

        self.apply_order_btn = QPushButton("Apply")
        self.apply_order_btn.clicked.connect(self._apply_custom_order)
        order_row.addWidget(self.apply_order_btn)
        layout.addLayout(order_row)

        group.setLayout(layout)

        outer = QVBoxLayout()
        outer.addWidget(group)
        outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer)

    def set_channels(self, channels: List[ChannelInfo]):
        """Populate the channel list with discovered channels."""
        self._channels = list(channels)
        self.channel_list.clear()

        # Default sort: by port letter then channel number
        self._channels.sort(key=lambda c: (c.port, c.channel_number))

        for ch in self._channels:
            item = QListWidgetItem(ch.native_name)
            item.setData(Qt.UserRole, ch)
            self.channel_list.addItem(item)

        n = len(self._channels)
        self.count_label.setText(f"{n} channel{'s' if n != 1 else ''} enabled for TCP")
        self._emit_order()

    def get_ordered_channel_names(self) -> List[str]:
        """Return channel names in current display order."""
        names = []
        for i in range(self.channel_list.count()):
            item = self.channel_list.item(i)
            ch: ChannelInfo = item.data(Qt.UserRole)
            names.append(ch.native_name)
        return names

    def set_scan_enabled(self, enabled: bool):
        self.scan_btn.setEnabled(enabled)

    def _apply_custom_order(self):
        """Reorder channels based on the comma-separated channel number input."""
        text = self.order_input.text().strip()
        if not text:
            return

        try:
            numbers = [int(x.strip()) for x in text.split(',')]
        except ValueError:
            return

        # Build a lookup from channel number to ChannelInfo
        ch_by_num = {}
        for ch in self._channels:
            ch_by_num[ch.channel_number] = ch

        # Reorder: requested order first, then any remaining channels
        ordered = []
        seen = set()
        for num in numbers:
            if num in ch_by_num and num not in seen:
                ordered.append(ch_by_num[num])
                seen.add(num)

        # Append any channels not in the custom order
        for ch in self._channels:
            if ch.channel_number not in seen:
                ordered.append(ch)

        self._channels = ordered
        self.channel_list.clear()
        for ch in self._channels:
            item = QListWidgetItem(ch.native_name)
            item.setData(Qt.UserRole, ch)
            self.channel_list.addItem(item)

        self._emit_order()

    def _on_order_changed(self):
        self._emit_order()

    def _emit_order(self):
        names = self.get_ordered_channel_names()
        self.channel_order_changed.emit(names)

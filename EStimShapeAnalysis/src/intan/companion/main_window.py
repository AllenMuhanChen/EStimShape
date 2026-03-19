"""
Main Window
============
Application shell with:
    - Connection panel (top)
    - Channel panel (left sidebar)
    - Module area with tabs (center) — LFP module is the first tab

Threading model:
    - Main thread: PyQt GUI event loop
    - DataReaderThread: reads raw waveform blocks from TCP socket
    - QTimer: periodically triggers LFP processing + plot updates
"""

import traceback
from typing import Dict, List, Optional

import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QMessageBox, QSplitter, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QMutex, QMutexLocker

from intan_tcp_client import IntanTCPClient, ChannelInfo
from lfp_processor import StreamingLFPProcessor, LFPProcessorConfig
from src.intan.companion.connection_panel import ConnectionPanel
from src.intan.companion.channel_panel import ChannelPanel
from src.intan.companion.lfp_module import LFPModule


class DataReaderThread(QThread):
    """
    Background thread that continuously reads waveform data from the
    Intan TCP waveform socket and appends it to the LFP processor buffers.

    Emits:
        data_received(n_samples): after each successful read
        error_occurred(message): on read errors
    """

    data_received = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, client: IntanTCPClient, processor: StreamingLFPProcessor,
                 channel_names: List[str], parent=None):
        super().__init__(parent)
        self.client = client
        self.processor = processor
        self.channel_names = channel_names
        self._running = False
        self._mutex = QMutex()

    def run(self):
        self._running = True
        n_channels = len(self.channel_names)

        while self._running:
            try:
                result = self.client.read_waveform_data(n_channels)
                if result is None:
                    self.msleep(50)  # No data yet, wait a bit
                    continue

                timestamps, data = result
                n_samples = data.shape[1]

                # Build dict mapping channel names to their data rows
                channel_data = {}
                for i, ch_name in enumerate(self.channel_names):
                    if i < data.shape[0]:
                        channel_data[ch_name] = data[i, :]

                # Thread-safe append to processor buffers
                with QMutexLocker(self._mutex):
                    self.processor.append_wideband(channel_data)

                self.data_received.emit(n_samples)

            except Exception as e:
                if self._running:  # Don't emit if we're shutting down
                    self.error_occurred.emit(str(e))
                    self.msleep(200)

    def stop(self):
        self._running = False
        self.wait(3000)


class MainWindow(QMainWindow):
    """
    Main application window.

    Layout:
        ┌──────────────────────────────────┐
        │       Connection Panel            │
        ├─────────┬────────────────────────┤
        │ Channel │                        │
        │  Panel  │   Module Tabs          │
        │         │   (LFP Module, ...)    │
        │         │                        │
        └─────────┴────────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Intan LFP Analyzer")
        self.setMinimumSize(1200, 700)

        # Core objects
        self.client = IntanTCPClient()
        self.processor: Optional[StreamingLFPProcessor] = None
        self.reader_thread: Optional[DataReaderThread] = None
        self._channel_names: List[str] = []
        self._sample_rate: Optional[float] = None
        self._total_samples = 0
        self._is_streaming = False

        self._setup_ui()
        self._setup_menu()
        self._setup_timers()

    def _setup_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout()

        # Connection panel at top
        self.connection_panel = ConnectionPanel()
        self.connection_panel.connect_requested.connect(self._on_connect)
        self.connection_panel.disconnect_requested.connect(self._on_disconnect)
        main_layout.addWidget(self.connection_panel)

        # Horizontal splitter: channels | modules
        splitter = QSplitter(Qt.Horizontal)

        # Channel panel (left)
        self.channel_panel = ChannelPanel()
        self.channel_panel.scan_requested.connect(self._on_scan_channels)
        self.channel_panel.channel_order_changed.connect(self._on_channel_order_changed)
        splitter.addWidget(self.channel_panel)

        # Module tabs (right)
        self.module_tabs = QTabWidget()
        self.lfp_module = LFPModule()
        self.module_tabs.addTab(self.lfp_module, "LFP Analysis")
        # Future modules get added as additional tabs here
        splitter.addWidget(self.module_tabs)

        splitter.setSizes([250, 950])
        main_layout.addWidget(splitter, stretch=1)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — Connect to Intan RHX to begin")

    def _setup_menu(self):
        menu_bar = self.menuBar()

        # Streaming menu
        stream_menu = menu_bar.addMenu("Streaming")

        self.start_action = QAction("Start Streaming", self)
        self.start_action.triggered.connect(self._start_streaming)
        self.start_action.setEnabled(False)
        stream_menu.addAction(self.start_action)

        self.stop_action = QAction("Stop Streaming", self)
        self.stop_action.triggered.connect(self._stop_streaming)
        self.stop_action.setEnabled(False)
        stream_menu.addAction(self.stop_action)

    def _setup_timers(self):
        # Timer for periodic LFP processing + plot updates
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._process_and_update)

    # ── Connection handling ──────────────────────────────────────────

    def _on_connect(self, cmd_host: str, cmd_port: int,
                     wave_host: str, wave_port: int):
        """Handle connect button — establish TCP connections."""
        try:
            self.status_bar.showMessage("Connecting to command socket...")
            self.client.connect_command(cmd_host, cmd_port)

            self.status_bar.showMessage("Connecting to waveform socket...")
            self.client.connect_waveform(wave_host, wave_port)

            # Query system info
            self._sample_rate = self.client.get_sample_rate()
            ctrl_type = self.client.get_controller_type()

            self.connection_panel.set_connected(True, True)
            self.connection_panel.set_system_info(
                f"{ctrl_type}  |  {self._sample_rate:.0f} Hz"
            )
            self.channel_panel.set_scan_enabled(True)
            self.status_bar.showMessage(
                f"Connected — {ctrl_type} at {self._sample_rate:.0f} Hz"
            )

            # Auto-scan channels on connect
            self._on_scan_channels()

        except Exception as e:
            self.client.disconnect()
            self.connection_panel.set_connected(False, False)
            QMessageBox.critical(self, "Connection Error", str(e))
            self.status_bar.showMessage(f"Connection failed: {e}")

    def _on_disconnect(self):
        """Handle disconnect — stop streaming and close sockets."""
        self._stop_streaming()
        self.client.disconnect()
        self.connection_panel.set_connected(False, False)
        self.connection_panel.set_system_info("")
        self.channel_panel.set_scan_enabled(False)
        self.start_action.setEnabled(False)
        self.status_bar.showMessage("Disconnected")

    # ── Channel discovery ────────────────────────────────────────────

    def _on_scan_channels(self):
        """Scan for TCP-enabled channels on the Intan."""
        if not self.client.is_command_connected:
            return

        self.status_bar.showMessage("Scanning for TCP-enabled channels...")
        try:
            channels = self.client.discover_enabled_channels()
            self.channel_panel.set_channels(channels)

            if channels:
                self.start_action.setEnabled(True)
                self.status_bar.showMessage(
                    f"Found {len(channels)} TCP-enabled channel(s) — "
                    "ready to stream"
                )
            else:
                self.start_action.setEnabled(False)
                self.status_bar.showMessage(
                    "No TCP-enabled channels found — "
                    "enable channels in Intan RHX first "
                    "(set TCPDataOutputEnabled = true)"
                )

        except Exception as e:
            QMessageBox.warning(self, "Scan Error", str(e))
            self.status_bar.showMessage(f"Scan failed: {e}")

    def _on_channel_order_changed(self, names: List[str]):
        """Update channel order when user reorders in the panel."""
        self._channel_names = names
        self.lfp_module.set_channel_names(names)

    # ── Streaming control ────────────────────────────────────────────

    def _start_streaming(self):
        """Start the data acquisition and processing pipeline."""
        if self._is_streaming:
            return
        if not self._channel_names:
            QMessageBox.warning(self, "No Channels",
                                "No TCP-enabled channels found. "
                                "Scan channels first.")
            return

        try:
            # Ensure controller is stopped before configuring
            self.client.stop_running()

            # Flush any stale data from previous runs
            self.client.flush_waveform_buffer()

            # Create processor
            config = LFPProcessorConfig()
            self.processor = StreamingLFPProcessor(
                sample_rate=self._sample_rate,
                channel_names=self._channel_names,
                config=config,
            )
            self.lfp_module.set_channel_names(self._channel_names)

            # Start controller
            self.client.start_running()

            # Start reader thread
            self.reader_thread = DataReaderThread(
                self.client, self.processor, self._channel_names, self
            )
            self.reader_thread.data_received.connect(self._on_data_received)
            self.reader_thread.error_occurred.connect(self._on_reader_error)
            self.reader_thread.start()

            # Start process timer
            interval_ms = self.lfp_module.update_interval.value() * 1000
            self.process_timer.start(interval_ms)

            self._is_streaming = True
            self._total_samples = 0
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.lfp_module.set_status("Streaming...")
            self.status_bar.showMessage(
                f"Streaming {len(self._channel_names)} channels..."
            )

        except Exception as e:
            self._stop_streaming()
            QMessageBox.critical(self, "Streaming Error", str(e))

    def _stop_streaming(self):
        """Stop data acquisition and processing."""
        if not self._is_streaming:
            return

        self.process_timer.stop()

        if self.reader_thread is not None:
            self.reader_thread.stop()
            self.reader_thread = None

        try:
            self.client.stop_running()
        except Exception:
            pass

        self._is_streaming = False
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.lfp_module.set_status("Stopped")
        self.status_bar.showMessage("Streaming stopped")

    def _on_data_received(self, n_samples: int):
        """Called by reader thread when new data arrives."""
        self._total_samples += n_samples

    def _on_reader_error(self, message: str):
        """Called by reader thread on errors."""
        self.status_bar.showMessage(f"Reader error: {message}")

    # ── Periodic processing ──────────────────────────────────────────

    def _process_and_update(self):
        """
        Called by the process timer.
        Runs the LFP pipeline and updates the plots.
        """
        if self.processor is None:
            return

        try:
            success = self.processor.process()
            if not success:
                elapsed = self._total_samples / self._sample_rate if self._sample_rate else 0
                self.lfp_module.set_status(
                    f"Buffering... ({elapsed:.1f}s / "
                    f"{self.processor.config.analysis_window_seconds:.0f}s needed)"
                )
                return

            # Get results and update plots
            gamma_ab_ratios = self.processor.get_gamma_alpha_beta_ratios()

            self.lfp_module.update_plots(
                normalized_spectra=self.processor.normalized_spectra,
                band_powers=self.processor.band_powers,
                gamma_ab_ratios=gamma_ab_ratios,
            )

            elapsed = self._total_samples / self._sample_rate if self._sample_rate else 0
            self.status_bar.showMessage(
                f"Streaming — {elapsed:.1f}s acquired, "
                f"{len(self._channel_names)} ch, "
                f"LFP rate: {self.processor.lfp_rate:.0f} Hz"
            )

        except Exception as e:
            self.lfp_module.set_status(f"Error: {e}")
            traceback.print_exc()

    # ── Cleanup ──────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Clean shutdown on window close."""
        self._stop_streaming()
        self.client.disconnect()
        event.accept()

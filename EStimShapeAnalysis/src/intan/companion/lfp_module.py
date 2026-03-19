"""
LFP Module
==========
Real-time LFP analysis display module.

Two synchronized plots, matching the existing offline analysis style:

1. Power Spectrum Heatmap (like LFPSpectrumPlotter)
   - X-axis: frequency (0-150 Hz)
   - Y-axis: channels in spatial order
   - Color: relative power (normalized per frequency bin)

2. Band Power Profile (like LFPBandPowerPlotter)
   - X-axis: relative power (0-1)
   - Y-axis: channels in spatial order
   - Three line profiles: delta-theta, alpha-beta, gamma
   - Plus gamma/alpha-beta ratio overlay

Both update periodically from the streaming LFP processor.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QPushButton, QSplitter,
    QCheckBox
)
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class SpectrumHeatmapWidget(FigureCanvas):
    """
    Matplotlib canvas showing the relative power spectrum heatmap.
    Mirrors LFPSpectrumPlotter.plot().
    """

    def __init__(self, parent=None, width=8, height=5):
        self.fig = Figure(figsize=(width, height), tight_layout=True)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        self._img = None
        self._colorbar = None

    def update_plot(self, channel_names: List[str],
                    normalized_spectra: Dict[str, Tuple[np.ndarray, np.ndarray]],
                    freq_range: Tuple[float, float] = (0, 150)):
        """
        Redraw the heatmap with new spectral data.

        Args:
            channel_names: Ordered list of channel names (top to bottom).
            normalized_spectra: Dict[channel_name, (freqs, normalized_power)]
            freq_range: (min_freq, max_freq) for display
        """
        self.ax.clear()

        if not channel_names or not normalized_spectra:
            self.ax.set_title("Waiting for data...")
            self.draw_idle()
            return

        # Build power matrix in channel order
        first_key = next(iter(normalized_spectra))
        freqs, _ = normalized_spectra[first_key]

        # Apply frequency mask
        freq_mask = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
        freqs_masked = freqs[freq_mask]

        power_matrix = []
        labels = []
        for ch_name in channel_names:
            if ch_name not in normalized_spectra:
                continue
            _, power = normalized_spectra[ch_name]
            power_matrix.append(power[freq_mask])
            labels.append(ch_name)

        if not power_matrix:
            self.ax.set_title("No channel data")
            self.draw_idle()
            return

        power_matrix = np.array(power_matrix)

        im = self.ax.imshow(
            power_matrix, aspect='auto', origin='upper',
            interpolation='nearest',
            extent=[freqs_masked[0], freqs_masked[-1],
                    len(labels) - 0.5, -0.5],
            cmap='viridis', vmin=0, vmax=1
        )
        self.ax.set_yticks(np.arange(len(labels)))
        self.ax.set_yticklabels(labels, fontsize=8)
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Channel")
        self.ax.set_title("Relative Power Spectrum")

        # Only add colorbar once, then update
        if self._colorbar is None:
            self._colorbar = self.fig.colorbar(im, ax=self.ax, label="Relative Power")
        else:
            self._colorbar.update_normal(im)

        self.draw_idle()


class BandPowerWidget(FigureCanvas):
    """
    Matplotlib canvas showing band power profiles.
    Mirrors LFPBandPowerPlotter.plot() with an added gamma/alpha-beta ratio.
    """

    BAND_COLORS = {
        "delta-theta": "tab:blue",
        "alpha-beta": "tab:orange",
        "gamma": "tab:green",
    }

    def __init__(self, parent=None, width=5, height=5):
        self.fig = Figure(figsize=(width, height), tight_layout=True)
        # Two side-by-side subplots: band powers + ratio
        self.ax_bands = self.fig.add_subplot(121)
        self.ax_ratio = self.fig.add_subplot(122)
        super().__init__(self.fig)
        self.setParent(parent)

    def update_plot(self, channel_names: List[str],
                    band_powers: Dict[str, Dict[str, float]],
                    gamma_ab_ratios: Dict[str, float]):
        """
        Redraw band power profiles.

        Args:
            channel_names: Ordered list of channel names.
            band_powers: Dict[channel_name, Dict[band_name, relative_power]]
            gamma_ab_ratios: Dict[channel_name, ratio_value]
        """
        self.ax_bands.clear()
        self.ax_ratio.clear()

        if not channel_names or not band_powers:
            self.ax_bands.set_title("Waiting for data...")
            self.draw_idle()
            return

        # Collect band data in channel order
        labels = []
        band_data = {band: [] for band in self.BAND_COLORS}
        ratios = []

        for ch_name in channel_names:
            if ch_name not in band_powers:
                continue
            labels.append(ch_name)
            for band_name in self.BAND_COLORS:
                val = band_powers[ch_name].get(band_name, 0.0)
                band_data[band_name].append(val)
            ratios.append(gamma_ab_ratios.get(ch_name, np.nan))

        if not labels:
            self.ax_bands.set_title("No data")
            self.draw_idle()
            return

        y_positions = np.arange(len(labels))

        # Band power profiles
        for band_name, values in band_data.items():
            color = self.BAND_COLORS.get(band_name, None)
            self.ax_bands.plot(values, y_positions, marker='o',
                               markersize=4, label=band_name, color=color)

        self.ax_bands.set_yticks(y_positions)
        self.ax_bands.set_yticklabels(labels, fontsize=8)
        self.ax_bands.invert_yaxis()
        self.ax_bands.set_xlim(0, 1)
        self.ax_bands.set_xlabel("Relative Power")
        self.ax_bands.set_ylabel("Channel")
        self.ax_bands.set_title("Band Power")
        self.ax_bands.legend(loc="lower right", fontsize=7)

        # Gamma / alpha-beta ratio
        valid_ratios = np.array(ratios)
        self.ax_ratio.plot(valid_ratios, y_positions, 'o-',
                           markersize=4, color='tab:purple')
        self.ax_ratio.set_yticks(y_positions)
        self.ax_ratio.set_yticklabels([], fontsize=8)
        self.ax_ratio.invert_yaxis()
        self.ax_ratio.set_xlabel("γ / αβ Ratio")
        self.ax_ratio.set_title("Gamma / Alpha-Beta")
        self.ax_ratio.axvline(x=1.0, color='gray', linestyle='--', alpha=0.5)

        self.draw_idle()


class LFPModule(QWidget):
    """
    The LFP analysis module — first pluggable module for the application.

    Contains the spectrum heatmap and band power widgets, plus controls
    for analysis parameters.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._channel_names: List[str] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Controls row
        controls = QHBoxLayout()

        controls.addWidget(QLabel("Update interval (s):"))
        self.update_interval = QSpinBox()
        self.update_interval.setRange(1, 30)
        self.update_interval.setValue(2)
        self.update_interval.setToolTip(
            "How often to recompute and refresh the LFP plots"
        )
        controls.addWidget(self.update_interval)

        controls.addWidget(QLabel("Freq range:"))
        self.freq_min = QSpinBox()
        self.freq_min.setRange(0, 500)
        self.freq_min.setValue(0)
        controls.addWidget(self.freq_min)

        controls.addWidget(QLabel("—"))
        self.freq_max = QSpinBox()
        self.freq_max.setRange(1, 500)
        self.freq_max.setValue(150)
        controls.addWidget(self.freq_max)
        controls.addWidget(QLabel("Hz"))

        controls.addStretch()

        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        controls.addWidget(self.status_label)

        layout.addLayout(controls)

        # Plot area — side by side with splitter
        splitter = QSplitter(Qt.Horizontal)

        self.heatmap = SpectrumHeatmapWidget(self)
        splitter.addWidget(self.heatmap)

        self.band_plot = BandPowerWidget(self)
        splitter.addWidget(self.band_plot)

        splitter.setSizes([500, 400])
        layout.addWidget(splitter, stretch=1)

        self.setLayout(layout)

    def set_channel_names(self, names: List[str]):
        """Update the channel list for plotting."""
        self._channel_names = list(names)

    def update_plots(self, normalized_spectra: Dict,
                     band_powers: Dict,
                     gamma_ab_ratios: Dict):
        """Refresh both plots with new data from the processor."""
        freq_range = (self.freq_min.value(), self.freq_max.value())

        self.heatmap.update_plot(
            self._channel_names, normalized_spectra, freq_range
        )
        self.band_plot.update_plot(
            self._channel_names, band_powers, gamma_ab_ratios
        )
        self.status_label.setText("Updated")

    def set_status(self, text: str):
        self.status_label.setText(text)

#!/usr/bin/env python3
"""Interactive GUI to explore channel-decomposition clusterings live.

The batch tool ``explore_channel_decompositions`` dumps every (method, K) figure
to disk. This is the interactive counterpart: one window where you flip between
methods (KMeans / Ward / GMM / NMF / Archetypal Analysis) and slide K, and the
probe map + response-PCA scatter + soft-membership heatmap redraw instantly.
Fits are cached, so scrubbing back and forth is free.

It loads the ONE experiment in ``context`` (like ``run_cluster_app``), fitting
each (method, K) on demand. A "K-selection" button runs the full model-selection
sweep (BIC / silhouette / gap / cophenetic) and pops the diagnostic figure, so
you can decide K without leaving the window.

Run:  python -m src.analysis.cluster.run_channel_decomposition_app
      python -m src.analysis.cluster.run_channel_decomposition_app --mock
"""
import os
import sys

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSlider, QScrollArea, QApplication)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from src.cluster.probe_mapping import DBCChannelMapper
from src.cluster.mock_cluster_app import get_qapplication_instance
from src.pga.app.run_cluster_app import DbDataLoader
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context
from src.analysis.cluster.explore_channel_decompositions import (
    PLOT_BASE_DIR, K_RANGE, ChannelData,
    _METHOD_NAME, _fit_method, _partition_scores, sweep_method,
    load_channel_data, plot_k_selection,
    _plot_probe_map, _plot_scatter, _plot_membership_heatmap,
)

METHODS = ('kmeans', 'ward', 'gmm', 'nmf', 'aa')
K_MIN, K_MAX = 2, 12


class ChannelDecompositionExplorer(QWidget):
    """Live method/K browser over one experiment's channel responses."""

    def __init__(self, data: ChannelData, session_label: str,
                 methods=METHODS, save_dir: str = None):
        super().__init__()
        self.data = data
        self.session_label = session_label
        self.methods = list(methods)
        self.save_dir = save_dir

        self.current_method = self.methods[0]
        self.current_k = min(3, K_MAX)
        self._fit_cache = {}     # (method, k) -> Fit
        self._sweeps = None      # {method: MethodSweep}, filled by K-selection

        self.figure = Figure(figsize=(13, 7.5))
        self.canvas = FigureCanvas(self.figure)

        self._build_gui()
        self._render()

    # -- GUI construction ---------------------------------------------------

    def _build_gui(self):
        self.setWindowTitle(f"Channel decomposition explorer — {self.session_label}")

        self.method_buttons = {}
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Method:"))
        for m in self.methods:
            btn = QPushButton(_METHOD_NAME[m])
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, mm=m: self._on_method(mm))
            method_row.addWidget(btn)
            self.method_buttons[m] = btn
        method_row.addStretch(1)
        self.button_k_selection = QPushButton("Show K-selection diagnostics")
        self.button_k_selection.clicked.connect(self._on_k_selection)
        method_row.addWidget(self.button_k_selection)

        self.slider_k = QSlider(Qt.Horizontal)
        self.slider_k.setMinimum(K_MIN)
        self.slider_k.setMaximum(K_MAX)
        self.slider_k.setValue(self.current_k)
        self.slider_k.setTickPosition(QSlider.TicksBelow)
        self.slider_k.setTickInterval(1)
        self.slider_k.setPageStep(1)
        self.slider_k.valueChanged.connect(self._on_k)
        self.label_k = QLabel(f"K = {self.current_k}")
        k_row = QHBoxLayout()
        k_row.addWidget(QLabel("Clusters K:"))
        k_row.addWidget(self.slider_k, stretch=1)
        k_row.addWidget(self.label_k)

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setTextFormat(Qt.RichText)

        layout = QVBoxLayout(self)
        layout.addLayout(method_row)
        layout.addLayout(k_row)
        layout.addWidget(self.canvas, stretch=1)
        layout.addWidget(self.label_status)
        self._sync_method_buttons()

    def _sync_method_buttons(self):
        for m, btn in self.method_buttons.items():
            btn.setChecked(m == self.current_method)

    # -- events -------------------------------------------------------------

    def _on_method(self, method: str):
        self.current_method = method
        self._sync_method_buttons()
        self._render()

    def _on_k(self, value: int):
        self.current_k = int(value)
        self.label_k.setText(f"K = {self.current_k}")
        self._render()

    def _on_k_selection(self):
        self._show_k_selection()

    # -- fitting (cached) ---------------------------------------------------

    def _get_fit(self, method: str, k: int):
        key = (method, k)
        if key not in self._fit_cache:
            self._fit_cache[key] = _fit_method(method, self.data, k)
        return self._fit_cache[key]

    # -- rendering ----------------------------------------------------------

    def _render(self):
        fit = self._get_fit(self.current_method, self.current_k)
        is_soft = fit.memberships is not None

        self.figure.clear()
        name = _METHOD_NAME[self.current_method]
        if is_soft:
            axes = self.figure.subplots(
                1, 3, gridspec_kw={'width_ratios': [1.3, 2, 2]})
            _plot_probe_map(axes[0], self.data, fit.labels, f"{name} K={fit.k}\nprobe map")
            _plot_scatter(axes[1], self.data, fit.labels, f"{name} K={fit.k}\nresponse PCA")
            im = _plot_membership_heatmap(axes[2], self.data, fit)
            self.figure.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)
        else:
            axes = self.figure.subplots(
                1, 2, gridspec_kw={'width_ratios': [1.3, 2]})
            _plot_probe_map(axes[0], self.data, fit.labels, f"{name} K={fit.k}\nprobe map")
            _plot_scatter(axes[1], self.data, fit.labels, f"{name} K={fit.k}\nresponse PCA")
        self.figure.tight_layout()
        self.canvas.draw()
        self._update_status(fit)

    def _update_status(self, fit):
        scores = _partition_scores(fit)
        parts = []
        sil = scores.get('silhouette')
        if sil is not None and not np.isnan(sil):
            parts.append(f"silhouette <b>{sil:+.3f}</b> (max=best)")
        if fit.bic is not None:
            parts.append(f"BIC <b>{fit.bic:.1f}</b> / AIC {fit.aic:.1f} (min=best)")
        if fit.recon_error is not None:
            parts.append(f"reconstruction err <b>{fit.recon_error:.2f}</b>")
        ch = scores.get('calinski_harabasz')
        db = scores.get('davies_bouldin')
        if ch is not None and not np.isnan(ch):
            parts.append(f"CH {ch:.1f} (max) · DB {db:.2f} (min)")
        sizes = np.bincount(fit.labels, minlength=fit.k)
        parts.append("cluster sizes " + "/".join(str(int(s)) for s in sizes))

        hint = ""
        if self._sweeps is not None and self.current_method in self._sweeps:
            auto = self._sweeps[self.current_method].auto_k
            hint = "  &nbsp;|&nbsp; auto-K: " + ", ".join(
                f"{c}={v}" for c, v in auto.items() if v is not None)
        self.label_status.setText(
            f"<b>{_METHOD_NAME[fit.method]}</b>, K={fit.k} &nbsp;—&nbsp; "
            + " &nbsp;·&nbsp; ".join(parts) + hint)

    # -- K-selection diagnostics -------------------------------------------

    def _show_k_selection(self):
        """Run the full model-selection sweep (cached) and display the saved
        k_selection.png in a scrollable dialog, and refresh the auto-K hint."""
        self.button_k_selection.setText("Computing sweep…")
        self.button_k_selection.setEnabled(False)
        QApplication.processEvents()
        try:
            if self._sweeps is None:
                self._sweeps = {m: sweep_method(m, self.data, K_RANGE)
                                for m in self.methods}
            save_dir = self.save_dir or os.path.join(PLOT_BASE_DIR, "channel_decomp_explore")
            plot_k_selection(self.data, self._sweeps, save_dir)
            png = os.path.join(save_dir, "k_selection.png")
            self._popup_image(png, "K-selection diagnostics")
        finally:
            self.button_k_selection.setText("Show K-selection diagnostics")
            self.button_k_selection.setEnabled(True)
        self._update_status(self._get_fit(self.current_method, self.current_k))

    def _popup_image(self, png_path: str, title: str):
        if not os.path.exists(png_path):
            self.label_status.setText(f"Could not find {png_path}")
            return
        dialog = QScrollArea()
        dialog.setWindowTitle(title)
        label = QLabel()
        label.setPixmap(QPixmap(png_path))
        dialog.setWidget(label)
        dialog.resize(1000, 900)
        dialog.show()
        # Keep a reference so the window isn't garbage-collected.
        self._k_selection_dialog = dialog


def main():
    use_mock = '--mock' in sys.argv
    channel_mapper = DBCChannelMapper("A")

    if use_mock:
        from src.cluster.mock_cluster_app import MockDataLoader
        data_loader = MockDataLoader(channel_mapper)
        session_label = "MOCK"
        save_dir = os.path.join(PLOT_BASE_DIR, "channel_decomp_explore_mock")
    else:
        data_loader = DbDataLoader(context.ga_config.connection())
        session_label = context.ga_database
        session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
        save_dir = os.path.join(PLOT_BASE_DIR, session_id, "channel_decomp_explore")

    data = load_channel_data(data_loader, channel_mapper)

    app = get_qapplication_instance()
    window = ChannelDecompositionExplorer(data, session_label, save_dir=save_dir)
    window.resize(1400, 900)
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()

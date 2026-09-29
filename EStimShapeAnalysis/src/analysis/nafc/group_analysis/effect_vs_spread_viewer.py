"""
Interactive viewer for the estim-effect-vs-current-spread figures.

Pick the X-axis (current_per_second / corr half-distance / their ratio), the Y-axis
(signed effect / P(effect>0) / effect z-score / |effect|), the method (Gaussian-
kernel smoothing or single-predictor regression) and, for smoothed curves, the
permutation test (two-sided / one-sided "above" / off) and kernel bandwidth. Also:
  - Min trials: keep only specs with at least this many estim-ON AND estim-OFF
    trials (one threshold for both).
  - X range: fixed axis limits (or auto); specs outside are drawn at the edge.
    "Fit only inside x-range" drops them from the fit / curve as well.
The figure redraws in place; the toolbar zooms, pans and saves.

The data table is built ONCE at start-up (same COMPARISON_* config and cache as
plot_current_spread_vs_tuning.main_effect_vs_spread); every drawn figure is cached
too, so flipping back to a view is instant. Smoothed curves with the permutation
test are the slow ones (bootstrap + thousands of shuffles) — lower "Permutations"
while exploring.

Run this file, or call main_viewer().
"""

import sys
import time
import traceback
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtCore import Qt
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
                             QFormLayout, QHBoxLayout, QLabel, QMainWindow,
                             QSpinBox, QVBoxLayout, QWidget)

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis import plot_current_spread_vs_tuning as cs

# Combo-box entries: (label shown, key). Y keys map to an EFFECT_PLOTS key per
# method; a missing method means that Y isn't available for it.
X_CHOICES = (('current_per_second', 'current'),
             ('corr half-distance', 'half_distance'),
             ('current ÷ half-distance ratio', 'ratio'))
Y_CHOICES = (('signed effect (ON − OFF %)', {'smooth': 'smooth_effect', 'regress': 'reg_effect'}),
             ('P(effect > 0)', {'smooth': 'smooth_rate', 'regress': 'reg_rate'}),
             ('effect z-score', {'smooth': 'smooth_z', 'regress': 'reg_z'}),
             ('|effect| (magnitude)', {'smooth': 'smooth_mag'}))
METHOD_CHOICES = (('smoothed (Gaussian kernel)', 'smooth'),
                  ('regression (linear / logistic)', 'regress'))
# (label, perm_test, alternative)
TEST_CHOICES = (('two-sided', True, 'two-sided'),
                ('one-sided: above null', True, 'greater'),
                ('off', False, None))


class EffectVsSpreadViewer(QMainWindow):
    def __init__(self, points, trial_types, null_config,
                 min_trials=cs.COMPARISON_MIN_ON_TRIALS):
        """points / trial_types from cs.prepare_effect_points (build it with a low
        min_on_trials so the Min-trials control can go below the default);
        null_config = the table kwargs build_onoff_null_draws needs (start/exclude
        sessions, effect metric, required conditions); min_trials = the starting
        ON-and-OFF trial threshold."""
        super().__init__()
        self.points = points
        self.trial_types = trial_types
        self.null_config = null_config
        self._fig_cache = {}
        self._z_null_cache = {}
        self.setWindowTitle("Estim effect vs current spread")

        self.x_box = self._combo([c[0] for c in X_CHOICES])
        self.y_box = self._combo([c[0] for c in Y_CHOICES])
        self.method_box = self._combo([c[0] for c in METHOD_CHOICES])
        self.test_box = self._combo([c[0] for c in TEST_CHOICES])
        self.bw_box = QDoubleSpinBox()
        self.bw_box.setRange(0.02, 1.0)
        self.bw_box.setSingleStep(0.02)
        self.bw_box.setValue(cs.DEFAULT_RATIO_BW_FRAC)
        self.bw_box.setToolTip("Kernel bandwidth as a fraction of the X spread "
                               "(bigger = smoother)")
        self.perm_box = QSpinBox()
        self.perm_box.setRange(100, 50000)
        self.perm_box.setSingleStep(1000)
        self.perm_box.setValue(cs.RATIO_RATE_N_PERM)
        self.perm_box.setToolTip("Shuffles for the permutation test (fewer = faster)")
        self.polarity_box = QCheckBox("rows = polarity")
        self.polarity_box.setChecked(True)

        self.trials_box = QSpinBox()
        self.trials_box.setRange(0, 100000)
        self.trials_box.setValue(int(min_trials or 0))
        self.trials_box.setToolTip("Keep specs with at least this many estim-ON AND "
                                   "estim-OFF trials")
        self.xauto_box = QCheckBox("auto")
        self.xmin_box, self.xmax_box = QDoubleSpinBox(), QDoubleSpinBox()
        for w in (self.xmin_box, self.xmax_box):
            w.setRange(-1e7, 1e7)
            w.setDecimals(2)
        self.xrestrict_box = QCheckBox("fit only inside x-range")
        self.xrestrict_box.setToolTip("Drop specs outside the x-range from the fit / "
                                      "smoothed curve too (otherwise they are fitted "
                                      "and drawn as arrows at the edge)")
        for w in (self.bw_box, self.perm_box, self.trials_box, self.xmin_box,
                  self.xmax_box):
            w.setKeyboardTracking(False)  # redraw on Enter/arrows, not every keystroke

        controls = QFormLayout()
        controls.addRow("X-axis", self.x_box)
        controls.addRow("Y-axis", self.y_box)
        controls.addRow("Method", self.method_box)
        controls.addRow("Test", self.test_box)
        controls.addRow("Bandwidth", self.bw_box)
        controls.addRow("Permutations", self.perm_box)
        controls.addRow("", self.polarity_box)
        controls.addRow("Min trials (ON && OFF)", self.trials_box)  # && = literal &
        xrange_row = QHBoxLayout()
        xrange_row.addWidget(self.xmin_box)
        xrange_row.addWidget(QLabel("to"))
        xrange_row.addWidget(self.xmax_box)
        xrange_row.addWidget(self.xauto_box)
        controls.addRow("X range", xrange_row)
        controls.addRow("", self.xrestrict_box)
        self.status = QLabel()
        self.status.setWordWrap(True)
        # the figure's long legend-style title lives here instead of above the plot
        self.legend = QLabel()
        self.legend.setWordWrap(True)
        self.legend.setStyleSheet("color: #444;")
        side = QVBoxLayout()
        side.addLayout(controls)
        side.addWidget(self.status)
        side.addSpacing(12)
        side.addWidget(self.legend)
        side.addStretch(1)
        side_widget = QWidget()
        side_widget.setLayout(side)
        side_widget.setFixedWidth(400)

        self.plot_area = QVBoxLayout()
        self.canvas = None
        self.toolbar = None
        plot_widget = QWidget()
        plot_widget.setLayout(self.plot_area)

        root = QHBoxLayout()
        root.addWidget(side_widget)
        root.addWidget(plot_widget, 1)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        self.x_box.currentIndexChanged.connect(self._reset_xrange)
        for box in (self.x_box, self.y_box, self.method_box, self.test_box):
            box.currentIndexChanged.connect(self.redraw)
        for box in (self.bw_box, self.perm_box, self.trials_box, self.xmin_box,
                    self.xmax_box):
            box.valueChanged.connect(self.redraw)
        for box in (self.polarity_box, self.xauto_box, self.xrestrict_box):
            box.stateChanged.connect(self.redraw)
        self.xauto_box.stateChanged.connect(self._sync_xrange_enabled)
        self._reset_xrange()
        self.redraw()

    @staticmethod
    def _combo(labels):
        box = QComboBox()
        box.addItems(labels)
        box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        return box

    # -- selection ----------------------------------------------------------
    def _selection(self):
        x_key = X_CHOICES[self.x_box.currentIndex()][1]
        method = METHOD_CHOICES[self.method_box.currentIndex()][1]
        plot_key = Y_CHOICES[self.y_box.currentIndex()][1].get(method)
        _, perm_test, alternative = TEST_CHOICES[self.test_box.currentIndex()]
        return x_key, method, plot_key, perm_test, alternative

    def _sync_enabled(self, method):
        """Grey out Y options the method can't draw, and the smoothing-only
        controls under regression."""
        model = self.y_box.model()
        for i, (_, per_method) in enumerate(Y_CHOICES):
            item = model.item(i)
            flags = item.flags()
            item.setFlags(flags | Qt.ItemIsEnabled if method in per_method
                          else flags & ~Qt.ItemIsEnabled)
        smooth = method == 'smooth'
        for w in (self.test_box, self.bw_box, self.perm_box):
            w.setEnabled(smooth)

    # -- x-range / trial filter -------------------------------------------------
    def _x_col(self):
        return cs.EFFECT_X_AXES[X_CHOICES[self.x_box.currentIndex()][1]]['col']

    def _reset_xrange(self, *_):
        """On an X-axis switch, load that axis's default limits: its fixed xlim
        (e.g. RATIO_XLIM) if it has one, else 'auto' with the boxes pre-filled from
        the data's robust range as a starting point for editing."""
        x_key = X_CHOICES[self.x_box.currentIndex()][1]
        default = cs.EFFECT_X_AXES[x_key]['xlim']
        lims = default or cs._robust_limits(self.points[self._x_col()]) or (0.0, 1.0)
        for w in (self.xmin_box, self.xmax_box, self.xauto_box):
            w.blockSignals(True)  # one redraw for the whole reset, not three
        self.xmin_box.setValue(lims[0])
        self.xmax_box.setValue(lims[1])
        self.xauto_box.setChecked(default is None)
        for w in (self.xmin_box, self.xmax_box, self.xauto_box):
            w.blockSignals(False)
        self._sync_xrange_enabled()

    def _sync_xrange_enabled(self, *_):
        manual = not self.xauto_box.isChecked()
        for w in (self.xmin_box, self.xmax_box, self.xrestrict_box):
            w.setEnabled(manual)

    def _xlim(self):
        """(lo, hi) from the boxes, None for auto, or 'bad' if lo >= hi."""
        if self.xauto_box.isChecked():
            return None
        lo, hi = round(self.xmin_box.value(), 6), round(self.xmax_box.value(), 6)
        return (lo, hi) if lo < hi else 'bad'

    def _filtered_points(self, min_trials, xlim, restrict):
        """Specs with >= min_trials estim-ON AND estim-OFF trials, and (when
        restrict) an x inside xlim."""
        pts = self.points
        n_on = pd.to_numeric(pts['n_on'], errors='coerce')
        n_off = pd.to_numeric(pts['n_off'], errors='coerce')
        keep = (n_on >= min_trials) & (n_off >= min_trials)
        if restrict and xlim:
            x = pd.to_numeric(pts[self._x_col()], errors='coerce')
            keep &= (x >= xlim[0]) & (x <= xlim[1])
        return pts[keep.to_numpy(dtype=bool)]

    # -- nulls ---------------------------------------------------------------
    def _nulls(self, plot_key, perm_test, n_perm):
        """(raw-effect null, z null) this smoothed plot's ON/OFF test needs."""
        family, mode, _ = cs.EFFECT_PLOTS[plot_key]
        if (family != 'smooth' or not perm_test
                or cs.RATIO_RATE_NULL_MODE != 'onoff'):
            return None, None
        if mode == 'z':
            if n_perm not in self._z_null_cache:
                self._z_null_cache[n_perm] = cs.build_onoff_null_z_draws(
                    self.points, n_draws=n_perm)
            return None, self._z_null_cache[n_perm]
        if mode in ('signed_split', 'abs'):  # these modes run no test
            return None, None
        # cached across calls by _cached_table
        return cs.build_onoff_null_draws(self.trial_types, n_draws=n_perm,
                                         **self.null_config), None

    # -- drawing -------------------------------------------------------------
    def redraw(self, *_):
        x_key, method, plot_key, perm_test, alternative = self._selection()
        self._sync_enabled(method)
        if plot_key is None:
            self._clear_figure()
            self.legend.setText("")
            self.status.setText("That Y-axis isn't available for this method — "
                                "pick another.")
            return
        smooth = method == 'smooth'
        bw = round(self.bw_box.value(), 4)
        n_perm = self.perm_box.value()
        by_polarity = self.polarity_box.isChecked()
        min_trials = self.trials_box.value()
        xlim = self._xlim()
        if xlim == 'bad':
            self.status.setText("X range: the minimum must be below the maximum.")
            return
        restrict = self.xrestrict_box.isChecked() and xlim is not None
        shared = (x_key, plot_key, by_polarity, min_trials, xlim, restrict)
        # regression figures don't depend on the smoothing-only settings
        key = (shared + (perm_test, alternative, bw, n_perm)) if smooth else shared

        fig = self._fig_cache.get(key)
        if fig is None:
            self.status.setText("Computing…" + (" (smoothed curves with the "
                                "permutation test can take a while)"
                                if smooth and perm_test else ""))
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            t0 = time.time()
            try:
                pts = self._filtered_points(min_trials, xlim, restrict)
                if len(pts) == 0:
                    QApplication.restoreOverrideCursor()
                    self._clear_figure()
                    self.legend.setText("")
                    self.status.setText("No specs pass the trial threshold / x-range.")
                    return
                # nulls are keyed per spec, so the full-table draws serve any subset
                onoff_null, onoff_null_z = self._nulls(plot_key, perm_test, n_perm)
                fig = cs.draw_effect_vs_spread(
                    pts, x_key, plot_key, trial_types=self.trial_types,
                    onoff_null=onoff_null, onoff_null_z=onoff_null_z,
                    by_polarity=by_polarity, bw_frac=bw, perm_test=perm_test,
                    n_perm=n_perm, alternative=alternative, xlim=xlim)
            except Exception as exc:  # keep the viewer alive; show what failed
                QApplication.restoreOverrideCursor()
                traceback.print_exc()
                self.status.setText(f"Failed: {type(exc).__name__}: {exc}")
                return
            QApplication.restoreOverrideCursor()
            if fig is None:
                self.status.setText("Nothing to plot for this selection.")
                return
            plt.close(fig)  # the viewer owns it now, not pyplot
            self._fit_to_window(fig)
            fig._viewer_n = len(pts)
            self._fig_cache[key] = fig
            self.status.setText(f"Drew {self._describe(plot_key, x_key, smooth, perm_test, alternative)}"
                                f" in {time.time() - t0:.1f}s.")
        else:
            self.status.setText(f"{self._describe(plot_key, x_key, smooth, perm_test, alternative)}"
                                " (cached).")
        self.status.setText(self.status.text() + f"\n{fig._viewer_n} of "
                            f"{len(self.points)} specs pass the filters.")
        self.legend.setText(fig._viewer_legend)
        self._show_figure(fig)

    @staticmethod
    def _describe(plot_key, x_key, smooth, perm_test, alternative):
        test = ((f", {alternative} test" if perm_test else ", no test") if smooth else "")
        return f"{plot_key} vs {x_key}{test}"

    @staticmethod
    def _fit_to_window(fig):
        """The batch figures are sized for a large PNG; in the window, move the
        long legend-style suptitle to the side panel (stored on the figure) and
        shrink the per-panel titles so neighbouring stats lines don't collide."""
        sup = fig._suptitle
        fig._viewer_legend = sup.get_text() if sup is not None else ""
        if sup is not None:
            sup.set_text("")
        for ax in fig.axes:
            ax.title.set_fontsize(7.5)
            ax.xaxis.label.set_fontsize(8)
            ax.yaxis.label.set_fontsize(8)
            ax.tick_params(labelsize=7.5)

    def _clear_figure(self):
        for w in (self.toolbar, self.canvas):
            if w is not None:
                self.plot_area.removeWidget(w)
                w.setParent(None)
        self.canvas = self.toolbar = None

    def _show_figure(self, fig):
        self._clear_figure()
        self.canvas = FigureCanvas(fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.plot_area.addWidget(self.toolbar)
        self.plot_area.addWidget(self.canvas, 1)
        self.canvas.draw_idle()


def main_viewer():
    """Build the effect points once with the shared COMPARISON_* config, then open
    the viewer."""
    config = cs._comparison_config_kwargs()
    config.pop('save_dir')
    config.pop('by_polarity')  # a viewer control
    # load every spec; the viewer's Min-trials control applies the threshold
    # (to ON and OFF trials alike), starting at the configured value
    min_trials = config.pop('min_on_trials')
    config['min_on_trials'] = 0
    print("Loading data (first run reads the DB and computes half-distances)…")
    trial_types, _, points = cs.prepare_effect_points(**config)
    if len(points) == 0:
        print("Nothing to plot.")
        return
    null_config = {k: config[k] for k in ('start_session_id', 'exclude_session_ids',
                                          'effect_metric', 'base_required_conditions')}
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = EffectVsSpreadViewer(points, trial_types, null_config,
                                  min_trials=min_trials)
    viewer.resize(1700, 1000)
    viewer.show()
    app.exec_()


if __name__ == '__main__':
    main_viewer()

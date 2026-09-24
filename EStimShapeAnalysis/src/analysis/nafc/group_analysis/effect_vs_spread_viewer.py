"""
Interactive viewer for the estim-effect-vs-current-spread figures.

Pick the X-axis (current_per_second / corr half-distance / their ratio), the Y-axis
(signed effect / P(effect>0) / effect z-score / |effect|), the method (Gaussian-
kernel smoothing or single-predictor regression) and, for smoothed curves, the
permutation test (two-sided / one-sided "above" / off) and kernel bandwidth. The
figure redraws in place; the toolbar zooms, pans and saves.

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
    def __init__(self, points, trial_types, null_config):
        """points / trial_types from cs.prepare_effect_points; null_config = the
        table kwargs build_onoff_null_draws needs (start/exclude sessions, effect
        metric, required conditions)."""
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
        for w in (self.bw_box, self.perm_box):
            w.setKeyboardTracking(False)  # redraw on Enter/arrows, not every keystroke

        controls = QFormLayout()
        controls.addRow("X-axis", self.x_box)
        controls.addRow("Y-axis", self.y_box)
        controls.addRow("Method", self.method_box)
        controls.addRow("Test", self.test_box)
        controls.addRow("Bandwidth", self.bw_box)
        controls.addRow("Permutations", self.perm_box)
        controls.addRow("", self.polarity_box)
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

        for box in (self.x_box, self.y_box, self.method_box, self.test_box):
            box.currentIndexChanged.connect(self.redraw)
        for box in (self.bw_box, self.perm_box):
            box.valueChanged.connect(self.redraw)
        self.polarity_box.stateChanged.connect(self.redraw)
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
        # regression figures don't depend on the smoothing-only settings
        key = ((x_key, plot_key, perm_test, alternative, bw, n_perm, by_polarity)
               if smooth else (x_key, plot_key, by_polarity))

        fig = self._fig_cache.get(key)
        if fig is None:
            self.status.setText("Computing…" + (" (smoothed curves with the "
                                "permutation test can take a while)"
                                if smooth and perm_test else ""))
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            t0 = time.time()
            try:
                onoff_null, onoff_null_z = self._nulls(plot_key, perm_test, n_perm)
                fig = cs.draw_effect_vs_spread(
                    self.points, x_key, plot_key, trial_types=self.trial_types,
                    onoff_null=onoff_null, onoff_null_z=onoff_null_z,
                    by_polarity=by_polarity, bw_frac=bw, perm_test=perm_test,
                    n_perm=n_perm, alternative=alternative)
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
            self._fig_cache[key] = fig
            self.status.setText(f"Drew {self._describe(plot_key, x_key, smooth, perm_test, alternative)}"
                                f" in {time.time() - t0:.1f}s.")
        else:
            self.status.setText(f"{self._describe(plot_key, x_key, smooth, perm_test, alternative)}"
                                " (cached).")
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
    print("Loading data (first run reads the DB and computes half-distances)…")
    trial_types, _, points = cs.prepare_effect_points(**config)
    if len(points) == 0:
        print("Nothing to plot.")
        return
    null_config = {k: config[k] for k in ('start_session_id', 'exclude_session_ids',
                                          'effect_metric', 'base_required_conditions')}
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = EffectVsSpreadViewer(points, trial_types, null_config)
    viewer.resize(1700, 1000)
    viewer.show()
    app.exec_()


if __name__ == '__main__':
    main_viewer()

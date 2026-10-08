"""
GUI for exploring EStim effects across conditions, any which way — the interactive
counterpart of average_estim_groups_by_condition.

Data: every EStimEffects condition for the chosen metric / algorithm label, with its
condition keys, estim parameters (polarity, shape, a1, num_channels, …), current
spread (current_per_second, correlation half-distance, ratio) and session metrics
as columns (see estim_condition_table). Loaded once per metric / algorithm label.

Left panel:
  - Sessions: tick which sessions to include (defaults to the shared COMPARISON_*
    session range / exclusions).
  - Min trials: keep conditions with at least this many estim-ON AND estim-OFF trials.
  - Filters: "Add filter…" any column. Categorical columns get a tick-list of
    values; numeric ones a min / max range (inclusive) with "keep missing".
  - Layout: X-axis by / Colour by / Panels by — any column (or session_id). A
    numeric column with many values is binned; edit its bin edges (comma
    separated) next to the dropdown. "x labels": your own tick labels, one per x
    point left to right (comma separated, or ';' if a label has a comma; blank
    keeps that tick's value; \\n breaks a line). "fill" puts the current ticks in
    the box to edit. Cleared when the X-axis column changes.
  - Plot: effect bars (mean of per-session mean effects ± SEM across sessions) or
    ON vs OFF dots, with the permutation test against the stored
    EStimPermutationTests nulls (two-sided / greater / less / off).
  - Stats box (on by default): to the right of the plot, the test used and each
    bar's p-value, plus the pairwise tests (Holm-corrected p) when Compare is on.
  - Copy summary table: the numbers behind the plot, tab-separated, to the clipboard.
  - Style: font sizes and x-label rotation. "Save as default" stores them in
    ~/.estim_condition_explorer/style_defaults.json, used at every start-up.
  - Save spec… / Load spec…: the whole setup (metric, algorithm label, sessions,
    min trials, filters, layout incl. bin edges and x labels, plot options, style)
    as a JSON file.
The figure redraws in place; the toolbar zooms, pans and saves. RIGHT-CLICK a panel
to copy just that panel (or the whole figure) to the clipboard as an image.

Run this file, or call main_gui().
"""

import io
import json
import math
import sys
import traceback
import zlib
from itertools import combinations
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor, QImage
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
                             QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QFileDialog, QListWidget, QListWidgetItem, QMainWindow,
                             QMenu, QPushButton, QScrollArea, QSpinBox, QVBoxLayout,
                             QWidget)

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis import estim_condition_table as ect

CLIPBOARD_DPI = 200
DEFAULT_MIN_TRIALS = 10
# a numeric column with more distinct values than this is binned when grouped on
MAX_CATEGORIES = 8
DEFAULT_N_BINS = 4
MISSING = 'missing'
OUTSIDE = 'outside bins'
# columns never offered for filtering / grouping
HIDDEN_COLUMNS = {'conditions', ect.EFFECT_COL, ect.ON_COL, ect.OFF_COL}
# (label, alternative) — None = no test
TEST_CHOICES = (('two-sided', 'two-sided'), ('one-sided: ON > OFF', 'greater'),
                ('one-sided: ON < OFF', 'less'), ('off', None))
PLOT_CHOICES = (('effect bars (ON − OFF)', 'bars'), ('ON vs OFF dots', 'dots'))
# individual points over each bar: (label, unit) — None = off
POINT_CHOICES = (('none', None), ('one per session', 'session'),
                 ('one per condition', 'condition'))
POINT_COLOR = '#222222'
# pairwise comparisons: (label, mode) — None = off
COMPARE_CHOICES = (('off', None), ('colours within each x', 'colors'),
                   ('x values within each colour', 'x'))
PAIR_ALPHA = 0.05
# (label, function) for the pairwise test
PAIR_TEST_CHOICES = (('permutation (within / between sessions)',
                      ect.pairwise_label_permutation),
                     ('Welch t-test on session means', ect.pairwise_welch))
NONE_LABEL = '(none)'
BAR_COLOR = '#4C72B0'
ON_COLOR, OFF_COLOR = '#D32F2F', '#333333'

# user settings: saved style defaults and a default folder for specs
SETTINGS_DIR = Path.home() / '.estim_condition_explorer'
STYLE_DEFAULTS_FILE = SETTINGS_DIR / 'style_defaults.json'
SPEC_VERSION = 1
# (key, label) of the font-size settings, in points
STYLE_FONTS = (('tick', 'Tick labels'), ('axis_label', 'Axis labels'),
               ('title', 'Panel titles'), ('legend', 'Legend'),
               ('stars', 'Stars / brackets'), ('n_label', 'n labels'),
               ('stats', 'Stats box'))
ROTATION_CHOICES = ('auto', '0', '30', '45', '90')
BUILTIN_STYLE = {'tick': 14, 'axis_label': 16, 'title': 16, 'legend': 13,
                 'stars': 15, 'n_label': 11, 'stats': 11, 'xtick_rotation': 'auto'}
# pairwise lines listed in the stats box before the rest are summarised
MAX_STATS_PAIRS = 12
# most of the figure width the stats box may take (its text shrinks to fit)
MAX_STATS_WIDTH = 0.45


def _load_style_defaults():
    """Built-in style, overridden by any saved defaults."""
    style = dict(BUILTIN_STYLE)
    try:
        saved = json.loads(STYLE_DEFAULTS_FILE.read_text())
        style.update({k: v for k, v in saved.items() if k in BUILTIN_STYLE})
    except (OSError, ValueError):
        pass
    return style


def _set_combo_text(box, text):
    """Select the entry with this text (editable boxes take any text); False if
    a non-editable box has no such entry."""
    if text is None:
        return False
    i = box.findText(str(text))
    if i >= 0:
        box.setCurrentIndex(i)
        return True
    if box.isEditable():
        box.setCurrentText(str(text))
        return True
    return False


def _compact(combo, chars=14):
    """Let a dropdown shrink to fit the side panel instead of growing to its
    longest entry."""
    combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(chars)
    return combo


def _default_session_range():
    """(start_session_id, exclude_session_ids) from the shared COMPARISON_* config."""
    try:
        from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
            COMPARISON_EXCLUDE_SESSION_IDS, COMPARISON_START_SESSION_ID)
        return COMPARISON_START_SESSION_ID, set(COMPARISON_EXCLUDE_SESSION_IDS or ())
    except Exception:
        return None, set()


def _numeric(series):
    """The series as floats if every non-missing value is numeric, else None."""
    num = pd.to_numeric(series, errors='coerce')
    return num if num.notna().sum() == series.notna().sum() else None


def _fmt(v):
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _sort_key(v):
    """Numbers numerically, then strings; 'missing' / 'outside bins' last."""
    if v in (MISSING, OUTSIDE):
        return (2, 0, str(v))
    try:
        return (0, float(v), '')
    except (TypeError, ValueError):
        return (1, 0, str(v))


def _default_edges(values, n_bins=DEFAULT_N_BINS):
    """Quantile bin edges, rounded to 2 significant figures."""
    q = np.nanquantile(values, np.linspace(0, 1, n_bins + 1))
    edges = []
    for v in q:
        r = float(f"{v:.2g}") if v != 0 else 0.0
        if not edges or r > edges[-1]:
            edges.append(r)
    edges[-1] = max(edges[-1], float(np.nanmax(values)))
    return edges


def _parse_edges(text):
    try:
        edges = [float(t) for t in text.replace(';', ',').split(',') if t.strip()]
    except ValueError:
        return None
    return edges if len(edges) >= 2 and all(a < b for a, b in zip(edges, edges[1:])) else None


def _parse_tick_labels(text):
    """Custom x tick labels: ';'-separated if the text has a ';', else comma
    separated; '\\n' becomes a line break, '' keeps that tick's own value."""
    if not text.strip():
        return []
    parts = text.split(';') if ';' in text else text.split(',')
    return [p.strip().replace('\\n', '\n') for p in parts]


def _bin_labels(values, edges):
    """'[lo, hi)' label per value (last bin closed), OUTSIDE / MISSING otherwise."""
    labels = [f"[{edges[i]:g}, {edges[i + 1]:g})" for i in range(len(edges) - 2)]
    labels.append(f"[{edges[-2]:g}, {edges[-1]:g}]")
    out = []
    for v in values:
        if v is None or not np.isfinite(v):
            out.append(MISSING)
        elif v < edges[0] or v > edges[-1]:
            out.append(OUTSIDE)
        else:
            i = min(int(np.searchsorted(edges, v, side='right')) - 1, len(labels) - 1)
            out.append(labels[i])
    return out, labels


class BadEdges(ValueError):
    pass


# ---------------------------------------------------------------------------
# Filter rows
# ---------------------------------------------------------------------------

class FilterRow(QFrame):
    """One filter on one column: a value tick-list (categorical) or a min / max
    range with 'keep missing' (numeric)."""

    def __init__(self, column, series, on_change, on_remove):
        super().__init__()
        self.column = column
        self.setFrameShape(QFrame.StyledPanel)
        self._num = _numeric(series)
        is_numeric = self._num is not None and self._num.nunique() > MAX_CATEGORIES
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        head = QHBoxLayout()
        head.addWidget(QLabel(f"<b>{column}</b>"))
        head.addStretch(1)
        remove = QPushButton("✕")
        remove.setFixedWidth(28)
        remove.clicked.connect(lambda: on_remove(self))
        head.addWidget(remove)
        layout.addLayout(head)

        self.values = self.lo = self.hi = self.keep_missing = None
        if is_numeric:
            row = QHBoxLayout()
            self.lo, self.hi = QDoubleSpinBox(), QDoubleSpinBox()
            for w, v in ((self.lo, self._num.min()), (self.hi, self._num.max())):
                w.setRange(-1e9, 1e9)
                w.setMinimumWidth(90)
                w.setDecimals(3)
                w.setValue(float(v))
                w.setKeyboardTracking(False)
                w.valueChanged.connect(on_change)
            self.keep_missing = QCheckBox("keep missing")
            self.keep_missing.setChecked(True)
            self.keep_missing.stateChanged.connect(on_change)
            row.addWidget(self.lo)
            row.addWidget(QLabel("to"))
            row.addWidget(self.hi)
            row.addWidget(self.keep_missing)
            layout.addLayout(row)
        else:
            self.values = QListWidget()
            labels = sorted({MISSING if pd.isna(v) else _fmt(v) for v in series},
                            key=_sort_key)
            for lab in labels:
                item = QListWidgetItem(lab)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.values.addItem(item)
            self.values.setMaximumHeight(min(22 * len(labels) + 6, 130))
            self.values.itemChanged.connect(on_change)
            layout.addWidget(self.values)

    def state(self):
        if self.values is not None:
            return {'column': self.column,
                    'checked': [self.values.item(i).text() for i in range(self.values.count())
                                if self.values.item(i).checkState() == Qt.Checked]}
        return {'column': self.column, 'lo': self.lo.value(), 'hi': self.hi.value(),
                'keep_missing': self.keep_missing.isChecked()}

    def set_state(self, state):
        widgets = [w for w in (self.values, self.lo, self.hi, self.keep_missing) if w]
        for w in widgets:
            w.blockSignals(True)
        if self.values is not None and 'checked' in state:
            checked = set(state['checked'])
            for i in range(self.values.count()):
                item = self.values.item(i)
                item.setCheckState(Qt.Checked if item.text() in checked else Qt.Unchecked)
        elif self.lo is not None and 'lo' in state:
            self.lo.setValue(state['lo'])
            self.hi.setValue(state['hi'])
            self.keep_missing.setChecked(state['keep_missing'])
        for w in widgets:
            w.blockSignals(False)

    def mask(self, df):
        col = df[self.column]
        if self.values is not None:
            checked = set(self.state()['checked'])
            labels = col.map(lambda v: MISSING if pd.isna(v) else _fmt(v))
            return labels.isin(checked).to_numpy(dtype=bool)
        num = pd.to_numeric(col, errors='coerce')
        inside = (num >= self.lo.value()) & (num <= self.hi.value())
        if self.keep_missing.isChecked():
            inside |= num.isna()
        return inside.to_numpy(dtype=bool)

    def describe(self):
        s = self.state()
        if 'checked' in s:
            n_all = self.values.count()
            if len(s['checked']) == n_all:
                return None
            return f"{self.column} ∈ {{{', '.join(s['checked'])}}}"
        miss = " (+missing)" if s['keep_missing'] else ""
        return f"{s['lo']:g} ≤ {self.column} ≤ {s['hi']:g}{miss}"


# ---------------------------------------------------------------------------
# Layout role rows (X-axis / Colour / Panels)
# ---------------------------------------------------------------------------

class RoleRow(QWidget):
    """Column dropdown, a 'bin' tick-box for numeric columns (on by default when
    the column has many values) and, when binning, the bin-edges box."""

    def __init__(self, allow_none, on_change):
        super().__init__()
        self.allow_none = allow_none
        self.on_change = on_change
        self.df = None
        self.combo = _compact(QComboBox(), 16)
        self.bin_box = QCheckBox("bin")
        self.bin_box.setToolTip("Group this numeric column into bins (edges below) "
                                "instead of one group per distinct value")
        self.edges = QLineEdit()
        self.edges.setPlaceholderText("bin edges")
        self.edges.setToolTip("Comma-separated bin edges for a numeric column, e.g. "
                              "0, 2, 4, 8 (bins [lo, hi), the last one closed)")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        top = QHBoxLayout()
        top.addWidget(self.combo, 1)
        top.addWidget(self.bin_box)
        layout.addLayout(top)
        layout.addWidget(self.edges)
        self.combo.currentIndexChanged.connect(self._column_changed)
        self.bin_box.stateChanged.connect(self._bin_toggled)
        self.edges.editingFinished.connect(on_change)

    def set_columns(self, df, columns, current=None):
        same = current == self.column()
        keep_edges = self.edges.text() if same else None
        keep_bin = self.bin_box.isChecked() if same else None
        self.df = df
        self.combo.blockSignals(True)
        self.combo.clear()
        if self.allow_none:
            self.combo.addItem(NONE_LABEL)
        self.combo.addItems(columns)
        if current is not None and self.combo.findText(current) >= 0:
            self.combo.setCurrentIndex(self.combo.findText(current))
        self.combo.blockSignals(False)
        self._column_changed(redraw=False)
        if keep_bin is not None:
            self.set_binning(keep_bin, keep_edges)

    def set_binning(self, on, edges=None):
        """Turn binning on / off (numeric columns only), optionally with edges."""
        if self._numeric_column() is None:
            return
        self.bin_box.blockSignals(True)
        self.bin_box.setChecked(bool(on))
        self.bin_box.blockSignals(False)
        self._bin_toggled(redraw=False)
        if on and edges:
            self.edges.setText(edges)

    def column(self):
        text = self.combo.currentText()
        return None if text in ('', NONE_LABEL) else text

    def _numeric_column(self):
        """The current column as floats if it is numeric with >= 2 values."""
        column = self.column()
        num = _numeric(self.df[column]) if column and self.df is not None else None
        return num if num is not None and num.nunique() >= 2 else None

    def _binnable(self, column):
        num = self._numeric_column() if column == self.column() else None
        return num if num is not None and self.bin_box.isChecked() else None

    def _column_changed(self, *_, redraw=True):
        num = self._numeric_column()
        self.bin_box.setVisible(num is not None)
        self.bin_box.blockSignals(True)
        self.bin_box.setChecked(num is not None and num.nunique() > MAX_CATEGORIES)
        self.bin_box.blockSignals(False)
        self.edges.setText("")
        self._bin_toggled(redraw=redraw)

    def _bin_toggled(self, *_, redraw=True):
        num = self._binnable(self.column())
        self.edges.setEnabled(num is not None)
        self.edges.setVisible(num is not None)
        if num is not None and not self.edges.text() and num.notna().any():
            self.edges.setText(", ".join(f"{e:g}" for e in _default_edges(num.dropna())))
        if redraw:
            self.on_change()

    def labels(self, df):
        """(per-row group label list, ordered categories) or (None, None) for no
        column; raises ValueError on bad bin edges."""
        column = self.column()
        if column is None:
            return None, None
        num = self._binnable(column)
        if num is not None:
            edges = _parse_edges(self.edges.text())
            if edges is None:
                raise BadEdges(f"{column}: bin edges must be ≥ 2 increasing numbers, "
                               "comma separated")
            values = pd.to_numeric(df[column], errors='coerce').to_numpy(dtype=float)
            labels, order = _bin_labels(values, edges)
            present = set(labels)
            order = order + [x for x in (OUTSIDE, MISSING) if x in present]
            return labels, [o for o in order if o in present]
        num = self._numeric_column()
        if num is not None:
            # unbinned numbers: whole numbers in full (spec ids), others to 4
            # significant figures (123.457 -> 123.5), so float noise shares a group
            labels = [MISSING if pd.isna(v) else
                      str(int(v)) if float(v).is_integer() else f"{v:.4g}"
                      for v in pd.to_numeric(df[column], errors='coerce')]
        else:
            labels = [MISSING if pd.isna(v) else _fmt(v) for v in df[column]]
        return labels, sorted(set(labels), key=_sort_key)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class EstimConditionExplorer(QMainWindow):
    def __init__(self, loader=ect.load_condition_table, null_loader=ect.load_permutation_nulls,
                 algorithm_labels=None, metric=ect.METRIC_PCT_HYP_VS_DELTA,
                 algorithm_label='none'):
        super().__init__()
        self.loader = loader
        self.null_loader = null_loader
        self._tables = {}
        self._nulls = {}
        self.df = None
        self.summary = None
        self.setWindowTitle("EStim condition explorer")
        self._redraw_timer = QTimer(self)
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.timeout.connect(self.redraw)

        # -- data --
        self.metric_box = _compact(QComboBox())
        self.metric_box.addItems(ect.METRICS)
        self.metric_box.setCurrentText(metric)
        self.algo_box = _compact(QComboBox())
        self.algo_box.addItems(algorithm_labels or [algorithm_label])
        self.algo_box.setCurrentText(algorithm_label)
        self.algo_box.setEditable(True)

        # -- sessions --
        self.session_list = QListWidget()
        self.session_list.setMaximumHeight(160)
        self.session_list.itemChanged.connect(self.schedule_redraw)
        sess_buttons = QHBoxLayout()
        for label, fn in (("all", lambda: self._check_sessions(lambda s: True)),
                          ("none", lambda: self._check_sessions(lambda s: False)),
                          ("defaults", self._default_sessions)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            sess_buttons.addWidget(b)

        self.trials_box = QSpinBox()
        self.trials_box.setRange(0, 100000)
        self.trials_box.setValue(DEFAULT_MIN_TRIALS)
        self.trials_box.setKeyboardTracking(False)
        self.trials_box.valueChanged.connect(self.schedule_redraw)

        # -- filters --
        self.filter_rows = []
        self.filter_area = QVBoxLayout()
        self.add_filter_box = _compact(QComboBox())
        self.add_filter_box.activated.connect(self._add_filter_from_box)

        # -- layout / plot --
        self.x_role = RoleRow(False, self.schedule_redraw)
        self.color_role = RoleRow(True, self.schedule_redraw)
        self.panel_role = RoleRow(True, self.schedule_redraw)
        self.xlabels_edit = QLineEdit()
        self.xlabels_edit.setPlaceholderText("custom x labels (optional)")
        self.xlabels_edit.setToolTip(
            "Your own x tick labels, one per x point left to right, comma separated "
            "(use ';' instead if a label has a comma). Leave an entry blank to keep "
            "that tick's value; \\n breaks a line. Cleared when the X-axis column "
            "changes.")
        self.xlabels_edit.editingFinished.connect(self.schedule_redraw)
        xlabels_fill = QPushButton("fill")
        xlabels_fill.setToolTip("Put the current x tick labels in the box to edit")
        xlabels_fill.clicked.connect(self._fill_xlabels)
        self.xlabels_row = QHBoxLayout()
        self.xlabels_row.addWidget(self.xlabels_edit, 1)
        self.xlabels_row.addWidget(xlabels_fill)
        # a new x column means new ticks, so old custom labels no longer apply
        self.x_role.combo.currentIndexChanged.connect(
            lambda *_: self.xlabels_edit.setText(""))
        self._x_ticks, self._x_names = [], {}
        self.plot_box = _compact(QComboBox())
        self.plot_box.addItems([c[0] for c in PLOT_CHOICES])
        self.test_box = _compact(QComboBox())
        self.test_box.addItems([c[0] for c in TEST_CHOICES])
        self.points_box = _compact(QComboBox())
        self.points_box.addItems([c[0] for c in POINT_CHOICES])
        self.points_box.setToolTip("Overlay individual data points: each session's mean "
                                   "(what the bar and its SEM summarise) or each "
                                   "condition")
        self.compare_box = _compact(QComboBox())
        self.compare_box.addItems([c[0] for c in COMPARE_CHOICES])
        self.compare_box.setToolTip(
            "Pairwise tests between bars, Holm-corrected across all pairs in the "
            "figure. Brackets mark pairs with corrected p < 0.05; every pair is in "
            "'Copy summary table'.")
        self.pair_test_box = _compact(QComboBox())
        self.pair_test_box.addItems([c[0] for c in PAIR_TEST_CHOICES])
        self.pair_test_box.setToolTip(
            "Welch t-test: unequal-variance t-test on the per-session means (one "
            "value per session per bar). Permutation: shuffles bar labels among a "
            "session's conditions where it has both, and whole sessions between the "
            "bars otherwise (no normality assumption; coarse p with few sessions).")
        self.n_box = QCheckBox("show n (conditions / sessions)")
        self.n_box.setChecked(True)
        self.stats_box = QCheckBox("stats box (test and p-values)")
        self.stats_box.setChecked(True)
        self.stats_box.stateChanged.connect(self.schedule_redraw)
        for w in (self.plot_box, self.test_box, self.points_box, self.compare_box,
                  self.pair_test_box):
            w.currentIndexChanged.connect(self.schedule_redraw)
        self.n_box.stateChanged.connect(self.schedule_redraw)
        copy_table = QPushButton("Copy summary table")
        copy_table.clicked.connect(self.copy_summary)

        # -- style --
        self.style_boxes = {}
        for key, _ in STYLE_FONTS:
            box = QSpinBox()
            box.setRange(4, 60)
            box.setSuffix(" pt")
            box.setKeyboardTracking(False)
            box.valueChanged.connect(self.schedule_redraw)
            self.style_boxes[key] = box
        self.rotation_box = _compact(QComboBox(), 6)
        self.rotation_box.addItems(ROTATION_CHOICES)
        self.rotation_box.setToolTip("x tick-label rotation (auto: 30° when there "
                                     "are more than 4 labels)")
        self.rotation_box.currentIndexChanged.connect(self.schedule_redraw)
        self.set_plot_style(_load_style_defaults(), redraw=False)
        style_buttons = QHBoxLayout()
        for label, fn in (("Save as default", self.save_style_default),
                          ("Built-in", lambda: self.set_plot_style(BUILTIN_STYLE))):
            b = QPushButton(label)
            b.clicked.connect(fn)
            style_buttons.addWidget(b)

        # -- specs --
        spec_buttons = QHBoxLayout()
        for label, fn in (("Save spec…", self.save_spec_dialog),
                          ("Load spec…", self.load_spec_dialog)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            spec_buttons.addWidget(b)

        form = QFormLayout()
        form.addRow(spec_buttons)
        form.addRow("Metric", self.metric_box)
        form.addRow("Algorithm label", self.algo_box)
        form.addRow(QLabel("<b>Sessions</b>"))
        form.addRow(self.session_list)
        form.addRow(sess_buttons)
        form.addRow("Min trials (ON && OFF)", self.trials_box)
        form.addRow(QLabel("<b>Filters</b>"))
        form.addRow(self.filter_area)
        form.addRow(self.add_filter_box)
        form.addRow(QLabel("<b>Layout</b>"))
        form.addRow("X-axis by", self.x_role)
        form.addRow("x labels", self.xlabels_row)
        form.addRow("Colour by", self.color_role)
        form.addRow("Panels by", self.panel_role)
        form.addRow(QLabel("<b>Plot</b>"))
        form.addRow("Plot", self.plot_box)
        form.addRow("Test", self.test_box)
        form.addRow("Points", self.points_box)
        form.addRow("Compare pairs", self.compare_box)
        form.addRow("Pairwise test", self.pair_test_box)
        form.addRow("", self.n_box)
        form.addRow("", self.stats_box)
        form.addRow(QLabel("<b>Style</b>"))
        for key, label in STYLE_FONTS:
            form.addRow(label, self.style_boxes[key])
        form.addRow("x-label rotation", self.rotation_box)
        form.addRow(style_buttons)
        form.addRow(copy_table)
        self.status = QLabel()
        self.status.setWordWrap(True)
        form.addRow(self.status)
        side = QWidget()
        side.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidget(side)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(520)

        self.plot_area = QVBoxLayout()
        self.figure = Figure(figsize=(10, 7))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.plot_area.addWidget(self.toolbar)
        self.plot_area.addWidget(self.canvas, 1)
        self.canvas.mpl_connect('button_press_event', self._on_click)
        plot_widget = QWidget()
        plot_widget.setLayout(self.plot_area)

        root = QHBoxLayout()
        root.addWidget(scroll)
        root.addWidget(plot_widget, 1)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        self.metric_box.currentIndexChanged.connect(self.reload)
        self.algo_box.activated.connect(self.reload)
        self.reload(first=True)

    # -- data loading ----------------------------------------------------------
    def _data_key(self):
        return self.algo_box.currentText(), self.metric_box.currentText()

    def reload(self, *_, first=False):
        if not self._ensure_loaded(self._data_key()):
            return
        self.df = self._tables[self._data_key()]
        if len(self.df) == 0:
            self.status.setText(f"No EStimEffects rows for {self._data_key()}.")
            return
        self._populate(first)

    def _ensure_loaded(self, key):
        """Load (and cache) the table + nulls for (algorithm label, metric);
        False if loading failed."""
        if key not in self._tables:
            self.status.setText(f"Loading {key}… (first load computes half-distances)")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            try:
                self._tables[key] = self.loader(*key)
                sessions = (sorted(self._tables[key]['session_id'].unique())
                            if len(self._tables[key]) else [])
                self._nulls[key] = self.null_loader(*key, session_ids=sessions)
            except Exception as exc:
                traceback.print_exc()
                self.status.setText(f"Load failed: {type(exc).__name__}: {exc}")
                return False
            finally:
                QApplication.restoreOverrideCursor()
        return True

    def _columns(self):
        cols = [c for c in self.df.columns if c not in HIDDEN_COLUMNS]
        return ['session_id'] + sorted(c for c in cols if c != 'session_id')

    def _populate(self, first, spec=None):
        """Fill the session list, filter choices and role dropdowns from self.df,
        keeping the current selections where they still apply — or taking them
        from spec (a dict from get_spec / a spec file)."""
        if spec is not None:
            prev_sessions = set(spec['sessions']) if 'sessions' in spec else None
        else:
            prev_sessions = None if first else {
                self.session_list.item(i).text() for i in range(self.session_list.count())
                if self.session_list.item(i).checkState() == Qt.Checked}
        self.session_list.blockSignals(True)
        self.session_list.clear()
        for sid in sorted(self.df['session_id'].unique()):
            item = QListWidgetItem(sid)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.session_list.addItem(item)
        self.session_list.blockSignals(False)
        if prev_sessions is None:
            self._default_sessions(redraw=False)
        else:
            self._check_sessions(lambda s: s in prev_sessions, redraw=False)

        columns = self._columns()
        self.add_filter_box.blockSignals(True)
        self.add_filter_box.clear()
        self.add_filter_box.addItem("Add filter…")
        self.add_filter_box.addItems(columns)
        self.add_filter_box.blockSignals(False)

        if spec is not None:
            states = spec.get('filters', [])
        elif first:
            states = [{'column': 'trial_type', 'checked': ['Hypothesized Shape', 'Delta Shape']},
                      {'column': 'ratio', 'lo': -1e9, 'hi': 8.0, 'keep_missing': True}]
        else:
            states = [r.state() for r in self.filter_rows]
        for row in list(self.filter_rows):
            self._remove_filter(row, redraw=False)
        for state in states:
            if state['column'] not in self.df.columns:
                continue
            if first and 'checked' in state and not (
                    set(state['checked']) & set(self.df[state['column']].dropna().map(_fmt))):
                continue  # none of the default values exist here
            row = self._add_filter(state['column'], redraw=False)
            if first and 'lo' in state and row.lo is not None:
                state = {**state, 'lo': row.lo.value()}
            row.set_state(state)

        defaults = {self.x_role: 'trial_type', self.color_role: 'polarity',
                    self.panel_role: None}
        spec_layout = (spec or {}).get('layout', {})
        for name, role in (('x', self.x_role), ('colour', self.color_role),
                           ('panels', self.panel_role)):
            if spec is not None and name in spec_layout:
                saved = spec_layout[name]
                role.set_columns(self.df, columns, saved.get('column'))
                # older specs have no 'bin': binned exactly when they stored edges
                role.set_binning(saved.get('bin', bool(saved.get('edges'))),
                                 saved.get('edges'))
                if role is self.x_role:
                    self.xlabels_edit.setText(saved.get('labels') or "")
            else:
                current = defaults[role] if first else role.column()
                role.set_columns(self.df, columns, current)
        self.redraw()

    def _check_sessions(self, predicate, redraw=True):
        self.session_list.blockSignals(True)
        for i in range(self.session_list.count()):
            item = self.session_list.item(i)
            item.setCheckState(Qt.Checked if predicate(item.text()) else Qt.Unchecked)
        self.session_list.blockSignals(False)
        if redraw:
            self.schedule_redraw()

    def _default_sessions(self, *_, redraw=True):
        start, excluded = _default_session_range()
        self._check_sessions(lambda s: (start is None or s >= start) and s not in excluded,
                             redraw=redraw)

    # -- filters -----------------------------------------------------------------
    def _add_filter_from_box(self, index):
        if index > 0:
            self._add_filter(self.add_filter_box.itemText(index))
        self.add_filter_box.setCurrentIndex(0)

    def _add_filter(self, column, redraw=True):
        row = FilterRow(column, self.df[column], self.schedule_redraw, self._remove_filter)
        self.filter_rows.append(row)
        self.filter_area.addWidget(row)
        if redraw:
            self.schedule_redraw()
        return row

    def _remove_filter(self, row, redraw=True):
        self.filter_rows.remove(row)
        self.filter_area.removeWidget(row)
        row.setParent(None)
        if redraw:
            self.schedule_redraw()

    def filtered(self):
        df = self.df
        sessions = {self.session_list.item(i).text() for i in range(self.session_list.count())
                    if self.session_list.item(i).checkState() == Qt.Checked}
        keep = df['session_id'].isin(sessions).to_numpy(dtype=bool, copy=True)
        n = self.trials_box.value()
        keep &= ((df[ect.N_ON_COL] >= n) & (df[ect.N_OFF_COL] >= n)).to_numpy(dtype=bool)
        for row in self.filter_rows:
            keep &= row.mask(df)
        return df[keep]

    # -- drawing -------------------------------------------------------------------
    def schedule_redraw(self, *_):
        self._redraw_timer.start(150)

    def redraw(self):
        if self.df is None or len(self.df) == 0:
            return
        try:
            self._draw()
        except BadEdges as exc:
            self.status.setText(str(exc))
        except Exception as exc:  # keep the GUI alive; show what failed
            traceback.print_exc()
            self.figure.clear()
            self.canvas.draw_idle()
            self.status.setText(f"Failed: {type(exc).__name__}: {exc}")

    def _draw(self):
        df = self.filtered()
        self.figure.clear()
        self.summary = None
        self.pairwise = None
        if len(df) == 0:
            self.canvas.draw_idle()
            self.status.setText("No conditions pass the filters.")
            return
        df = df.copy()
        orders = {}
        for name, role in (('__x', self.x_role), ('__color', self.color_role),
                           ('__panel', self.panel_role)):
            labels, order = role.labels(df)
            orders[name] = order or ['']
            # ordered categories, so the summary table sorts like the plot
            df[name] = pd.Categorical(labels if labels is not None else [''] * len(df),
                                      categories=orders[name], ordered=True)
        alternative = TEST_CHOICES[self.test_box.currentIndex()][1]
        summary = ect.summarize_groups(df, ['__panel', '__x', '__color'],
                                       nulls=self._nulls.get(self._data_key()),
                                       alternative=alternative)
        self.summary = summary.rename(columns={
            '__panel': self.panel_role.column() or 'panel',
            '__x': self.x_role.column(), '__color': self.color_role.column() or 'colour'})

        panels = [p for p in orders['__panel'] if (summary['__panel'] == p).any()]
        # custom x tick labels apply in order to the x values shown anywhere in
        # the figure, so a panel missing an x value still gets the right names
        self._x_ticks = [x for x in orders['__x'] if (summary['__x'] == x).any()]
        custom = _parse_tick_labels(self.xlabels_edit.text())
        self._x_names = {x: c for x, c in zip(self._x_ticks, custom) if c}
        n_cols = min(len(panels), 3)
        n_rows = math.ceil(len(panels) / n_cols)
        axes = self.figure.subplots(n_rows, n_cols, squeeze=False, sharey=True)
        colors = self._colors(orders['__color'])
        mode = PLOT_CHOICES[self.plot_box.currentIndex()][1]
        pairs = self._pairwise(df, summary, panels, orders)
        st = self.plot_style()
        positions = {}
        for ax, panel in zip(axes.flat, panels):
            positions[panel] = self._draw_panel(ax, summary[summary['__panel'] == panel],
                                                df[df['__panel'] == panel], orders,
                                                colors, mode)
            if self.panel_role.column():
                ax.set_title(f"{self.panel_role.column()} = {panel}",
                             fontsize=st['title'], fontweight='bold')
        for ax in list(axes.flat)[len(panels):]:
            ax.set_visible(False)
        if self.n_box.isChecked():
            # a strip below the lowest bar / star for the n labels (y is shared, so
            # setting it on one panel sets them all)
            y_lo, y_hi = axes.flat[0].get_ylim()
            pad = 0.03 * st['n_label'] / 11 + 0.05
            axes.flat[0].set_ylim(y_lo - pad * (y_hi - y_lo), y_hi)
        if pairs is not None:
            for ax, panel in zip(axes.flat, panels):
                self._draw_brackets(ax, pairs[pairs['__panel'] == panel], positions[panel])
        self._legend_handles = self._legend(colors, mode)
        if self._legend_handles:
            axes.flat[0].legend(handles=self._legend_handles, fontsize=st['legend'],
                                loc='best', title=self.color_role.column() or None,
                                title_fontsize=st['legend'])
        for ax in axes[:, 0]:
            ax.set_ylabel('EStim effect: ON − OFF (%)' if mode == 'bars'
                          else '% chose hypothesized', fontsize=st['axis_label'])
        for ax in axes[-1, :]:
            ax.set_xlabel(self.x_role.column(), fontsize=st['axis_label'])
        right = 1.0
        if self.stats_box.isChecked():
            text = self._stats_text(summary, pairs, panels, alternative)
            box = self.figure.text(0.995, 0.5, text, ha='right', va='center',
                                   multialignment='left', fontsize=st['stats'],
                                   bbox=dict(boxstyle='round,pad=0.5', fc='white',
                                             ec='#999999', lw=0.8))
            # shrink the text if the box would take more than MAX_STATS_WIDTH of
            # the figure or overflow its height, then give the plot the rest
            renderer = self.canvas.get_renderer()
            fig_w, fig_h = self.figure.bbox.width, self.figure.bbox.height
            while True:
                ext = box.get_window_extent(renderer)
                if (ext.width <= MAX_STATS_WIDTH * fig_w and ext.height <= 0.97 * fig_h) \
                        or box.get_fontsize() <= 6:
                    break
                box.set_fontsize(box.get_fontsize() - 1)
            right = max(1 - MAX_STATS_WIDTH, 1 - ext.width / fig_w - 0.02)
        self.figure.tight_layout(rect=(0, 0, right, 1))
        self.canvas.draw_idle()

        filt = [d for d in (r.describe() for r in self.filter_rows) if d]
        self.status.setText(
            f"{len(df)} of {len(self.df)} conditions, {df['session_id'].nunique()} sessions "
            f"pass the filters.\nFilters: {'; '.join(filt) if filt else 'none'}"
            + ("" if alternative else "\nTest off.")
            + (self._pairwise_note(pairs) if pairs is not None else "")
            + (f"\nx labels: {len(custom)} given for {len(self._x_ticks)} x points."
               if custom and len(custom) != len(self._x_ticks) else ""))

    @staticmethod
    def _colors(color_order):
        if color_order == ['']:
            return {'': BAR_COLOR}
        cmap = matplotlib.colormaps['tab10']
        return {c: (cmap(i % 10) if c not in (MISSING, OUTSIDE) else '#BBBBBB')
                for i, c in enumerate(color_order)}

    def _legend(self, colors, mode):
        handles = []
        if list(colors) != ['']:
            handles += [Patch(facecolor=col, label=lab) for lab, col in colors.items()]
        if mode == 'dots':
            handles += [Line2D([0], [0], marker='o', ls='', color=ON_COLOR, label='EStim ON'),
                        Line2D([0], [0], marker='o', ls='', mfc='white', color=OFF_COLOR,
                               label='EStim OFF')]
        return handles

    def _points(self, gdf):
        """Individual points of one bar: per-session means or per-condition rows
        (columns effect / on / off), or None when points are off."""
        unit = POINT_CHOICES[self.points_box.currentIndex()][1]
        cols = [ect.EFFECT_COL, ect.ON_COL, ect.OFF_COL]
        if unit is None or len(gdf) == 0:
            return None
        pts = gdf.groupby('session_id')[cols].mean() if unit == 'session' else gdf[cols]
        return pts.rename(columns={ect.EFFECT_COL: 'effect', ect.ON_COL: 'on',
                                   ect.OFF_COL: 'off'})

    @staticmethod
    def _jitter(n, half_width, seed):
        return np.random.default_rng(seed).uniform(-half_width, half_width, n)

    def _draw_panel(self, ax, summary, panel_df, orders, colors, mode):
        st = self.plot_style()
        x_order = [x for x in orders['__x'] if (summary['__x'] == x).any()]
        show_n = self.n_box.isChecked()
        positions = {}  # (x, colour) -> (bar centre, top of everything drawn for it)
        # one bar width for the panel (set by the most crowded x), so a lone bar
        # isn't drawn wider than its neighbours
        width = 0.8 / max(summary.groupby('__x')['__color'].nunique().max(), 1)
        for xi, x in enumerate(x_order):
            # only the colours present at this x share its slot, so the bars stay
            # centred on the tick (colour, not position, identifies the value)
            at_x = summary[summary['__x'] == x]
            c_order = [c for c in orders['__color'] if (at_x['__color'] == c).any()]
            for ci, c in enumerate(c_order):
                r = at_x[at_x['__color'] == c].iloc[0]
                pos = xi + width * (ci - (len(c_order) - 1) / 2)
                color = colors.get(c, BAR_COLOR)
                pts = self._points(panel_df[(panel_df['__x'] == x)
                                            & (panel_df['__color'] == c)])
                if mode == 'bars':
                    ax.bar(pos, r['effect'], width * 0.9, color=color, alpha=0.85,
                           edgecolor='black', linewidth=0.5)
                    ax.errorbar(pos, r['effect'], yerr=r['effect_sem'], color='black',
                                capsize=3, lw=1)
                    top = r['effect'] + (r['effect_sem'] if np.isfinite(r['effect_sem']) else 0)
                    bottom = r['effect'] - (r['effect_sem'] if np.isfinite(r['effect_sem']) else 0)
                    if pts is not None:
                        jit = self._jitter(len(pts), width * 0.25, (xi, ci))
                        ax.scatter(pos + jit, pts['effect'], s=10, color=POINT_COLOR,
                                   alpha=0.6, lw=0, zorder=3)
                        top = max(top, pts['effect'].max())
                        bottom = min(bottom, pts['effect'].min())
                    star_y = top if r['effect'] >= 0 else bottom
                    va = 'bottom' if r['effect'] >= 0 else 'top'
                else:
                    off_x, on_x = pos - width * 0.2, pos + width * 0.2
                    ax.plot([off_x, on_x], [r['off'], r['on']], color=color, lw=1.5)
                    ax.errorbar(off_x, r['off'], yerr=r['off_sem'], fmt='o', mfc='white',
                                color=OFF_COLOR, capsize=2, ms=5)
                    ax.errorbar(on_x, r['on'], yerr=r['on_sem'], fmt='o', color=ON_COLOR,
                                capsize=2, ms=5)
                    star_y = max(r['on'] + np.nan_to_num(r['on_sem']),
                                 r['off'] + np.nan_to_num(r['off_sem']))
                    if pts is not None:
                        # each unit's OFF -> ON pair, joined by a faint line
                        jit = self._jitter(len(pts), width * 0.06, (xi, ci))
                        for (_, p), j in zip(pts.iterrows(), jit):
                            ax.plot([off_x + j, on_x + j], [p['off'], p['on']],
                                    color=color, lw=0.6, alpha=0.4, zorder=1)
                        ax.scatter(off_x + jit, pts['off'], s=9, facecolor='white',
                                   edgecolor=OFF_COLOR, lw=0.6, alpha=0.7, zorder=2)
                        ax.scatter(on_x + jit, pts['on'], s=9, color=ON_COLOR,
                                   alpha=0.6, lw=0, zorder=2)
                        star_y = max(star_y, pts['on'].max(), pts['off'].max())
                    va = 'bottom'
                marker = ect.significance_marker(r['p'])
                if marker:
                    ax.annotate(marker, (pos, star_y), xytext=(0, 2 if va == 'bottom' else -2),
                                textcoords='offset points', ha='center', va=va,
                                fontsize=st['stars'])
                upper = max(star_y, 0) if mode == 'bars' else star_y
                positions[(x, c)] = (pos, upper)
                if show_n:
                    ax.annotate(f"{r['n_conditions']}/{r['n_sessions']}", (pos, 0),
                                xycoords=('data', 'axes fraction'), xytext=(0, 2),
                                textcoords='offset points', ha='center', va='bottom',
                                fontsize=st['n_label'], color='#555555')
        if mode == 'bars':
            ax.axhline(0, color='black', lw=0.8, ls='--')
        ax.set_xticks(range(len(x_order)))
        rotation = (30 if len(x_order) > 4 else 0) if st['xtick_rotation'] == 'auto' \
            else int(st['xtick_rotation'])
        ax.set_xticklabels([self._x_names.get(x, x) for x in x_order], rotation=rotation,
                           ha='right' if 0 < rotation < 90 else 'center',
                           rotation_mode='anchor', fontsize=st['tick'])
        ax.tick_params(axis='y', labelsize=st['tick'])
        ax.set_xlim(-0.6, len(x_order) - 0.4)
        ax.grid(True, axis='y', alpha=0.3)
        ax.spines[['top', 'right']].set_visible(False)
        return positions

    def _x_name(self, x):
        return self._x_names.get(x, x).replace('\n', ' ')

    @staticmethod
    def _p_text(p, n_null=None):
        if p is None or not np.isfinite(p):
            return "p = n/a"
        if p == 0 and n_null:
            return f"p < {1 / n_null:.1g}"
        return f"p = {p:.3f}" if p >= 0.001 else f"p = {p:.1g}"

    def _stats_text(self, summary, pairs, panels, alternative):
        """Text for the stats box: the test, each bar's p and the pairwise tests,
        grouped under a header per panel."""
        side = {'two-sided': 'two-sided', 'greater': 'one-sided, ON > OFF',
                'less': 'one-sided, ON < OFF'}
        panel_col = self.panel_role.column()

        def by_panel(rows_of_panel, indent="  "):
            out = []
            for panel in panels:
                rows = rows_of_panel(panel)
                if panel_col and rows:
                    out.append(f"{indent}{panel_col} = {panel}")
                pad = indent + ("  " if panel_col else "")
                out += [pad + r for r in rows]
            return out

        def p_line(name, p, n_null=None):
            return f"{name}: {self._p_text(p, n_null)} {ect.significance_marker(p)}".rstrip()

        lines = []
        if alternative is None:
            lines.append("Per-bar test: off")
        else:
            n_null = pd.to_numeric(summary.get('n_null'), errors='coerce').min() \
                if 'n_null' in summary else np.nan
            shuffles = f", {int(n_null):,} shuffles" if pd.notna(n_null) else ""
            lines += [f"Per-bar test: permutation ({side[alternative]})",
                      "EStim ON/OFF trial labels shuffled",
                      f"within each condition{shuffles}"]

            def bars(panel):
                rows = []
                for _, r in summary[summary['__panel'] == panel].iterrows():
                    if r['__x'] not in self._x_ticks:
                        continue
                    name = self._x_name(r['__x'])
                    if r['__color'] != '':
                        name += f", {r['__color']}"
                    n_null = r.get('n_null')
                    rows.append(p_line(name, r['p'], n_null if pd.notna(n_null) else None))
                return rows
            lines += by_panel(bars)
        if pairs is not None:
            if PAIR_TEST_CHOICES[self.pair_test_box.currentIndex()][1] is ect.pairwise_welch:
                lines += ["", "Pairwise: Welch t-test on per-session",
                          "mean effects, Holm-corrected"]
            else:
                lines += ["", "Pairwise: permutation, bar labels shuffled",
                          "within sessions (whole sessions when a",
                          "session has only one bar), Holm-corrected"]
            compare = COMPARE_CHOICES[self.compare_box.currentIndex()][1]
            shown = pairs if len(pairs) <= MAX_STATS_PAIRS else \
                pairs.nsmallest(MAX_STATS_PAIRS, 'p_holm')

            def pair_rows(panel):
                rows = []
                for _, r in shown[shown['__panel'] == panel].iterrows():
                    if compare == 'colors':   # colours at one x
                        fixed, a, b = self._x_name(r['fixed']), r['a'], r['b']
                    else:                     # x values for one colour
                        fixed, a, b = r['fixed'], self._x_name(r['a']), self._x_name(r['b'])
                    name = f"{fixed}: {a} vs {b}" if fixed != '' else f"{a} vs {b}"
                    rows.append(p_line(name, r['p_holm'] if pd.notna(r['p']) else None))
                return rows
            lines += by_panel(pair_rows)
            if len(pairs) > len(shown):
                lines.append(f"  (+{len(pairs) - len(shown)} more in the summary table)")
            if len(pairs) == 0:
                lines.append("  no pairs to compare")
        return "\n".join(lines)

    # -- pairwise comparisons ---------------------------------------------------------
    def _pairwise(self, df, summary, panels, orders):
        """Pairwise tests for the chosen Compare mode, Holm-corrected across every
        pair in the figure. DataFrame (one row per pair) or None when off."""
        compare = COMPARE_CHOICES[self.compare_box.currentIndex()][1]
        if compare is None:
            return None
        # compare 'colors': colours against each other at each x; 'x': x values
        # against each other for each colour
        fixed, varied = ('__x', '__color') if compare == 'colors' else ('__color', '__x')
        test = PAIR_TEST_CHOICES[self.pair_test_box.currentIndex()][1]
        rows = []
        for panel in panels:
            pdf = df[df['__panel'] == panel]
            psum = summary[summary['__panel'] == panel]
            for f in orders[fixed]:
                present = [v for v in orders[varied]
                           if ((psum[fixed] == f) & (psum[varied] == v)).any()]
                sub = pdf[pdf[fixed] == f]
                for a, b in combinations(present, 2):
                    if test is ect.pairwise_label_permutation:
                        seed = zlib.crc32(f"{panel}|{f}|{a}|{b}".encode())
                        res = test(sub, varied, a, b, seed=seed)
                    else:
                        res = test(sub, varied, a, b)
                    rows.append({'__panel': panel, 'fixed': f, 'a': a, 'b': b, **res})
        pairs = pd.DataFrame(rows)
        if len(pairs) == 0:
            pairs = pd.DataFrame(columns=['__panel', 'fixed', 'a', 'b', 'diff', 'p'])
        pairs['p_holm'] = ect.holm(list(pairs['p'])) if len(pairs) else []
        pairs['_compare'] = compare
        fixed_name = (self.x_role.column() if compare == 'colors'
                      else self.color_role.column() or 'colour')
        varied_name = (self.color_role.column() or 'colour' if compare == 'colors'
                       else self.x_role.column())
        self.pairwise = pairs.drop(columns='_compare').rename(columns={
            '__panel': self.panel_role.column() or 'panel', 'fixed': fixed_name,
            'a': f"{varied_name} A", 'b': f"{varied_name} B",
            'diff': 'diff (A − B)'})
        if not self.panel_role.column():
            self.pairwise = self.pairwise.drop(columns='panel')
        return pairs

    @staticmethod
    def _pairwise_note(pairs):
        if len(pairs) == 0:
            return "\nPairwise: no pairs to compare (need ≥ 2 bars per group)."
        tested = pairs['p'].notna().sum()
        sig = int((pairs['p_holm'].fillna(1) < PAIR_ALPHA).sum())
        untestable = len(pairs) - tested
        return (f"\nPairwise: {tested} pairs tested, {sig} significant after Holm "
                f"(p < {PAIR_ALPHA:g})"
                + (f"; {untestable} untestable (too few sessions)" if untestable else "")
                + ".")

    def _draw_brackets(self, ax, pairs, positions):
        """Brackets over pairs with Holm p < PAIR_ALPHA, stacked so they don't overlap."""
        sig = pairs[pairs['p_holm'].fillna(1) < PAIR_ALPHA]
        if len(sig) == 0:
            return
        y_lo, y_hi = ax.get_ylim()
        step = 0.06 * (y_hi - y_lo)
        spans = []
        for _, r in sig.iterrows():
            keys = ((r['fixed'], r['a']), (r['fixed'], r['b'])) if r['_compare'] == 'colors' \
                else ((r['a'], r['fixed']), (r['b'], r['fixed']))
            if keys[0] not in positions or keys[1] not in positions:
                continue
            x1, x2 = sorted(positions[k][0] for k in keys)
            spans.append((x2 - x1, x1, x2, r['p_holm']))
        placed = []  # (x1, x2, y)
        top = y_hi
        for _, x1, x2, p in sorted(spans):  # narrow brackets lowest
            base = max(u for (x, u) in positions.values() if x1 - 1e-9 <= x <= x2 + 1e-9)
            y = base + step
            for px1, px2, py in placed:
                if px1 <= x2 and x1 <= px2:  # overlapping span -> go above it
                    y = max(y, py + step)
            placed.append((x1, x2, y))
            ax.plot([x1, x1, x2, x2], [y - step * 0.3, y, y, y - step * 0.3],
                    color='black', lw=0.9)
            ax.text((x1 + x2) / 2, y, ect.significance_marker(p), ha='center',
                    va='bottom', fontsize=self.plot_style()['stars'])
            top = max(top, y + step)
        ax.set_ylim(y_lo, top)

    def _fill_xlabels(self):
        """Put the current x ticks (custom names where set) in the box to edit."""
        names = [self._x_names.get(x, x).replace('\n', '\\n')
                 for x in self._x_ticks]
        sep = '; ' if any(',' in n for n in names) else ', '
        self.xlabels_edit.setText(sep.join(names))

    # -- style ----------------------------------------------------------------------
    def plot_style(self):
        style = {key: box.value() for key, box in self.style_boxes.items()}
        style['xtick_rotation'] = self.rotation_box.currentText()
        return style

    def set_plot_style(self, style, redraw=True):
        widgets = [*self.style_boxes.values(), self.rotation_box]
        for w in widgets:
            w.blockSignals(True)
        for key, box in self.style_boxes.items():
            if key in style:
                box.setValue(int(style[key]))
        _set_combo_text(self.rotation_box, style.get('xtick_rotation'))
        for w in widgets:
            w.blockSignals(False)
        if redraw:
            self.schedule_redraw()

    def save_style_default(self):
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            STYLE_DEFAULTS_FILE.write_text(json.dumps(self.plot_style(), indent=2))
        except OSError as exc:
            self._note(f"Could not save style defaults: {exc}")
            return
        self._note(f"Saved style defaults to {STYLE_DEFAULTS_FILE}.")

    # -- specs -----------------------------------------------------------------------
    def get_spec(self):
        """The whole current setup as a JSON-serialisable dict."""
        def role(r):
            return {'column': r.column(), 'bin': r.bin_box.isChecked(),
                    'edges': r.edges.text() if r.edges.isEnabled() else None}
        layout = {'x': role(self.x_role), 'colour': role(self.color_role),
                  'panels': role(self.panel_role)}
        layout['x']['labels'] = self.xlabels_edit.text()
        return {
            'version': SPEC_VERSION,
            'metric': self.metric_box.currentText(),
            'algorithm_label': self.algo_box.currentText(),
            'sessions': [self.session_list.item(i).text()
                         for i in range(self.session_list.count())
                         if self.session_list.item(i).checkState() == Qt.Checked],
            'min_trials': self.trials_box.value(),
            'filters': [r.state() for r in self.filter_rows],
            'layout': layout,
            'plot': {'plot': self.plot_box.currentText(),
                     'test': self.test_box.currentText(),
                     'points': self.points_box.currentText(),
                     'compare': self.compare_box.currentText(),
                     'pairwise_test': self.pair_test_box.currentText(),
                     'show_n': self.n_box.isChecked(),
                     'show_stats': self.stats_box.isChecked()},
            'style': self.plot_style(),
        }

    def apply_spec(self, spec):
        """Restore a setup from get_spec / a spec file. Settings that no longer
        apply (a missing column, session or option) are skipped and reported."""
        skipped = []
        for box, key in ((self.metric_box, 'metric'), (self.algo_box, 'algorithm_label')):
            box.blockSignals(True)
            if key in spec and not _set_combo_text(box, spec[key]):
                skipped.append(f"{key} {spec[key]!r}")
            box.blockSignals(False)
        if not self._ensure_loaded(self._data_key()):
            return
        self.df = self._tables[self._data_key()]
        if len(self.df) == 0:
            self.status.setText(f"No EStimEffects rows for {self._data_key()}.")
            return
        plot = spec.get('plot', {})
        widgets = [self.trials_box, self.plot_box, self.test_box, self.points_box,
                   self.compare_box, self.pair_test_box, self.n_box, self.stats_box]
        for w in widgets:
            w.blockSignals(True)
        if 'min_trials' in spec:
            self.trials_box.setValue(int(spec['min_trials']))
        for box, key in ((self.plot_box, 'plot'), (self.test_box, 'test'),
                         (self.points_box, 'points'), (self.compare_box, 'compare'),
                         (self.pair_test_box, 'pairwise_test')):
            if key in plot and not _set_combo_text(box, plot[key]):
                skipped.append(f"{key} {plot[key]!r}")
        if 'show_n' in plot:
            self.n_box.setChecked(bool(plot['show_n']))
        if 'show_stats' in plot:
            self.stats_box.setChecked(bool(plot['show_stats']))
        for w in widgets:
            w.blockSignals(False)
        if 'style' in spec:
            self.set_plot_style(spec['style'], redraw=False)
        known = set(self.df['session_id'])
        missing_sessions = [s for s in spec.get('sessions', []) if s not in known]
        if missing_sessions:
            skipped.append(f"{len(missing_sessions)} session(s) not in the data")
        missing_cols = [f['column'] for f in spec.get('filters', [])
                        if f['column'] not in self.df.columns]
        missing_cols += [r['column'] for r in spec.get('layout', {}).values()
                         if r.get('column') and r['column'] not in self.df.columns]
        if missing_cols:
            skipped.append("column(s) " + ", ".join(sorted(set(missing_cols))))
        self._populate(False, spec=spec)
        if skipped:
            self._note("Spec loaded; skipped: " + "; ".join(skipped) + ".")

    def _spec_dir(self):
        folder = SETTINGS_DIR / 'specs'
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            folder = Path.home()
        return str(folder)

    def save_spec_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save spec", self._spec_dir(),
                                              "Spec (*.json)")
        if path:
            self.save_spec(path if path.endswith('.json') else path + '.json')

    def load_spec_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load spec", self._spec_dir(),
                                              "Spec (*.json)")
        if path:
            self.load_spec(path)

    def save_spec(self, path):
        try:
            Path(path).write_text(json.dumps(self.get_spec(), indent=2))
        except OSError as exc:
            self._note(f"Could not save spec: {exc}")
            return
        self._note(f"Saved spec to {path}.")

    def load_spec(self, path):
        try:
            spec = json.loads(Path(path).read_text())
        except (OSError, ValueError) as exc:
            self._note(f"Could not read spec: {exc}")
            return
        self.apply_spec(spec)
        self.setWindowTitle(f"EStim condition explorer — {Path(path).stem}")

    # -- clipboard -------------------------------------------------------------------
    def copy_summary(self):
        if self.summary is None:
            return
        text = self.summary.to_csv(sep='\t', index=False)
        if self.pairwise is not None and len(self.pairwise):
            text += ("\nPairwise comparisons (within-session label permutation, "
                     "Holm-corrected)\n" + self.pairwise.to_csv(sep='\t', index=False))
        QApplication.clipboard().setText(text)
        self._note("Copied the summary table to the clipboard.")

    def _note(self, text):
        self.status.setText(self.status.text().split("\nCopied")[0] + "\n" + text)

    def _on_click(self, event):
        """Right-click (outside the toolbar's pan/zoom modes) -> copy menu."""
        if event.button != 3 or getattr(self.toolbar.mode, 'value', self.toolbar.mode):
            return
        menu = QMenu(self)
        copy_panel = menu.addAction("Copy this panel")
        copy_panel.setEnabled(event.inaxes is not None)
        copy_all = menu.addAction("Copy whole figure")
        chosen = menu.exec_(QCursor.pos())
        if chosen is copy_panel and event.inaxes is not None:
            self.copy_panel(event.inaxes)
        elif chosen is copy_all:
            self.copy_figure()

    @staticmethod
    def _to_clipboard(png_bytes):
        QApplication.clipboard().setImage(QImage.fromData(png_bytes, 'PNG'))

    def copy_figure(self):
        buf = io.BytesIO()
        self.figure.savefig(buf, format='png', dpi=CLIPBOARD_DPI, bbox_inches='tight')
        self._to_clipboard(buf.getvalue())
        self._note("Copied the whole figure to the clipboard.")
        return buf.getvalue()

    def copy_panel(self, ax):
        """Copy one panel as a PNG, with its axis labels and the colour legend even
        if (in the grid) only the edge panels / first panel carry them."""
        fig = self.figure
        panels = [a for a in fig.axes if a.get_visible()]
        xlab = next((a.get_xlabel() for a in panels if a.get_xlabel()), '')
        ylab = next((a.get_ylabel() for a in panels if a.get_ylabel()), '')
        old = (ax.get_xlabel(), ax.get_ylabel())
        had_legend = ax.get_legend() is not None
        # shared-y panels off the first column hide their tick labels
        had_yticklabels = any(t.label1.get_visible() for t in ax.yaxis.get_major_ticks())
        st = self.plot_style()
        ax.set_xlabel(old[0] or xlab, fontsize=st['axis_label'])
        ax.set_ylabel(old[1] or ylab, fontsize=st['axis_label'])
        ax.tick_params(axis='y', labelleft=True)
        if not had_legend and self._legend_handles:
            ax.legend(handles=self._legend_handles, fontsize=st['legend'], loc='best',
                      title=self.color_role.column(), title_fontsize=st['legend'])
        others = [a for a in panels if a is not ax]
        for a in others:
            a.set_visible(False)
        try:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=CLIPBOARD_DPI, bbox_inches='tight',
                        pad_inches=0.08)
        finally:
            for a in others:
                a.set_visible(True)
            ax.set_xlabel(old[0])
            ax.set_ylabel(old[1])
            ax.tick_params(axis='y', labelleft=had_yticklabels)
            if not had_legend and ax.get_legend() is not None:
                ax.get_legend().remove()
            self.canvas.draw_idle()
        self._to_clipboard(buf.getvalue())
        self._note("Copied the panel to the clipboard.")
        return buf.getvalue()


def main_gui():
    app = QApplication.instance() or QApplication(sys.argv)
    try:
        labels = ect.list_algorithm_labels()
    except Exception:
        labels = None
    # the EStimEffects pipeline's default label ('None' / 'none'), else the first
    default = next((l for l in labels or [] if str(l).lower() == 'none'),
                   (labels or ['none'])[0])
    gui = EstimConditionExplorer(algorithm_labels=labels, algorithm_label=default)
    gui.resize(1700, 1000)
    gui.show()
    app.exec_()


if __name__ == '__main__':
    main_gui()

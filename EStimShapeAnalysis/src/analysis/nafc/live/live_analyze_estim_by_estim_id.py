"""
live_analyze_estim_by_estim_id.py
---------------------------------
Live GUI version of analyze_estim_by_estim_id's Plot 1 (the EStimSpecId overview),
built on pyqtgraph so updates are cheap and never disturb the user's scroll/zoom.

On a timer it:
    1. polls the experiment DB for newly-completed choice trials,
    2. compiles just those trials into EStimShapeTrials (allen_data_repository),
    3. re-reads EStimShapeTrials, recomputes the metric curves, and pushes the new data
       into the existing pyqtgraph curves via setData — no figure rebuild.

Because the plots/axes/view-boxes are created once and only the curve *data* changes, the
scroll position and any pan/zoom the user has applied are preserved across refreshes, and a
refresh landing mid-scroll does not yank the view around.

Layout: a vertical-scrolling grid of independent PlotWidgets — rows are metrics, columns are
Delta / Variant [/ Removed]. The mouse wheel scrolls the page (forwarded to the scroll area);
drag pans/zooms an individual plot.

Scope (intentionally minimal for now):
    - Plot 1 only: % Hypothesized, % Rand Choice, % Hypothesized vs Delta
      (and % Removed Choice when removed trials/choices exist).
    - No permutation tests, no optional filtering/combining. start_gen_id is honoured.

Run:
    python -m src.analysis.nafc.live.live_analyze_estim_by_estim_id
"""

import sys

# Force matplotlib to a non-GUI backend BEFORE anything imports pyplot (the compile path
# pulls in matplotlib). Otherwise matplotlib may load a Qt binding that conflicts with the
# one pyqtgraph uses, and mixing two Qt bindings in one process segfaults (SIGSEGV).
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import pyqtgraph as pg
# Use pyqtgraph's Qt shim so every Qt class comes from the SAME binding pyqtgraph selected.
# Importing PyQt5 directly alongside pyqtgraph risks a binding mismatch -> SIGSEGV.
from pyqtgraph.Qt import QtWidgets, QtCore

from clat.util.connection import Connection
from src.startup import context
from src.repository.export_to_repository import read_session_id_and_date_from_db_name

from src.analysis.nafc.analyze_estim_by_estim_id import partition_estim_data
from src.analysis.nafc.live.live_estim_compile import (
    REPO_DB, ensure_estimshape_trials_table, compile_new_trials, get_existing_trial_starts,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_POLL_SECONDS = 5
START_GEN_ID = 1                 # keep start_gen_id; trials below this are not plotted
PLOT_HEIGHT = 300                # px per panel; the column of panels scrolls vertically
# Experimental stim types that make up Plot 1 (matches analyze_estim_by_estim_id.main).
_EXPERIMENTAL_STIM_TYPES = ['EStimShapeVariantsDeltaNAFCStim', 'EStimShapeVariantsDeletedNAFCStim']

# (row_title, metric_kind) for the metric rows; the removed row is appended when relevant.
_BASE_ROWS = [
    ('% Hypothesized',           'hypothesized'),
    ('% Rand Choice',            'rand'),
    ('% Hypothesized vs Delta',  'hyp_vs_delta'),
]
_REMOVED_ROW = ('% Removed Choice', 'removed')

# tab10-ish palette for per-spec curves; EStim OFF is always black/dashed.
_SPEC_COLORS = [
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189),
    (140, 86, 75), (227, 119, 194), (127, 127, 127), (188, 189, 34), (23, 190, 207),
]
# ---------------------------------------------------------------------------

pg.setConfigOptions(antialias=True, background='w', foreground='k')


def _qt_enum(enum_cls_name, member):
    """Resolve a Qt enum value across bindings: PyQt6/PySide6 scope enums under their class
    (Qt.PenStyle.DashLine) while PyQt5 exposes them flat (Qt.DashLine). pyqtgraph may bind to
    either, so try the scoped form first and fall back to the flat one."""
    enum_cls = getattr(QtCore.Qt, enum_cls_name, None)
    if enum_cls is not None and hasattr(enum_cls, member):
        return getattr(enum_cls, member)
    return getattr(QtCore.Qt, member)


_SCROLLBAR_OFF = _qt_enum('ScrollBarPolicy', 'ScrollBarAlwaysOff')
_DASH_LINE = _qt_enum('PenStyle', 'DashLine')


def read_session_trials_as_exp_format(session_id, start_gen_id=START_GEN_ID):
    """Read this session's rows from EStimShapeTrials and map them back to the experiment-DB
    column names the partitioning expects. Applies the start_gen_id cut and restricts to
    experimental stim types."""
    conn = Connection(REPO_DB)
    conn.execute("""
        SELECT task_id, estim_spec_id, is_estim_on, is_hypothesized_choice,
               is_correct_choice, trial_type, noise_chance, base_mstick_id,
               gen_id, trial_start, sample_length, trial_class, choice
        FROM EStimShapeTrials
        WHERE session_id = %s
        ORDER BY task_id
    """, (session_id,))
    column_names = [desc[0] for desc in conn.my_cursor.description]
    rows = conn.fetch_all()
    db = pd.DataFrame(rows, columns=column_names)
    if len(db) == 0:
        return db

    out = pd.DataFrame(index=db.index)
    out['NoiseChance']    = db['noise_chance']
    out['IsHypothesized'] = db['is_hypothesized_choice'].astype(bool)
    out['IsCorrect']      = db['is_correct_choice'].astype(bool)
    out['EStimEnabled']   = db['is_estim_on'].astype(bool)
    out['EStimSpecId']    = db['estim_spec_id']
    out['Choice']         = db['choice']
    out['SampleLength']   = db['sample_length']
    out['GenId']          = db['gen_id']
    out['BaseMStickId']   = db['base_mstick_id']
    out['StimType']       = db['trial_class']
    out['IsDelta']        = db['trial_type'] == 'Delta Shape'
    out['IsRemovedTrial'] = db['trial_type'] == 'Removed Trial'
    # Readable trial-type label used by the behavioral filter.
    out['TrialType'] = np.where(out['IsRemovedTrial'], 'Removed Trial',
                                np.where(out['IsDelta'], 'Delta Shape', 'Hypothesized Shape'))

    out = out[out['GenId'] >= start_gen_id]
    out = out[out['StimType'].isin(_EXPERIMENTAL_STIM_TYPES)]
    return out


# ---------------------------------------------------------------------------
# Metric aggregation
# ---------------------------------------------------------------------------

def _metric_series(df, kind):
    """Return (possibly-filtered df, boolean series) for a metric kind, matching the
    semantics of the matplotlib panels in analyze_estim_by_estim_id."""
    if kind == 'hyp_vs_delta':
        d = df[~df['Choice'].isin(['rand', 'removed'])]
        d = d[~((d['IsRemovedTrial'] == True) & (d['Choice'] == 'match'))]
        return d, d['IsHypothesized'].astype(bool)
    if kind == 'rand':
        return df, (df['Choice'] == 'rand')
    if kind == 'removed':
        return df, ((df['Choice'] == 'removed') |
                    ((df['IsRemovedTrial'] == True) & (df['Choice'] == 'match')))
    return df, df['IsHypothesized'].astype(bool)  # 'hypothesized'


def curve_points(df, kind):
    """Aggregate a metric to (noise_pct, percent, n) arrays sorted by noise level."""
    if df is None or len(df) == 0:
        return [], [], []
    d, vals = _metric_series(df, kind)
    if len(d) == 0:
        return [], [], []
    work = pd.DataFrame({'noise': d['NoiseChance'].to_numpy(),
                         'v': np.asarray(vals, dtype=float)})
    grp = work.groupby('noise')['v']
    pct = grp.mean() * 100.0
    n = grp.count()
    xs = [float(noise) * 100.0 for noise in pct.index]
    return xs, [float(v) for v in pct.values], [int(c) for c in n.values]


def _rows_for(include_removed):
    return list(_BASE_ROWS) + ([_REMOVED_ROW] if include_removed else [])


def _columns_for(partition):
    """(col_key, col_title, estim_on_df, estim_off_df, spec_ids) per Delta/Variant[/Removed]."""
    cols = [
        ('delta',   'Delta',   partition.data_delta_on,   partition.data_delta_off,   partition.delta_spec_ids),
        ('variant', 'Variant', partition.data_variant_on, partition.data_variant_off, partition.variant_spec_ids),
    ]
    if partition.include_removed:
        cols.append(('removed', 'Removed', partition.data_removed_on,
                     partition.data_removed_off, partition.removed_spec_ids))
    return cols


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

LEGEND_WIDTH = 170  # px reserved to the right of each plot for its legend


class _ScrollGraphicsLayout(pg.GraphicsLayoutWidget):
    """GraphicsLayoutWidget (holds a plot + a legend beside it) whose wheel scrolls the
    surrounding QScrollArea (page scroll) instead of zooming. Mouse drag still pans/zooms."""

    def __init__(self, scroll_area, **kwargs):
        super().__init__(**kwargs)
        self._scroll_area = scroll_area

    def wheelEvent(self, ev):
        bar = self._scroll_area.verticalScrollBar()
        bar.setValue(bar.value() - ev.angleDelta().y())
        ev.accept()


class _MultiCheckFilter(QtWidgets.QWidget):
    """A labelled row of checkboxes (one per distinct value) for including/excluding a
    behavioral parameter. Values are added (checked) as they first appear in the data and the
    user's selections persist. selected() returns the set of checked values, or None when all
    are checked (i.e. no filtering)."""

    def __init__(self, title, on_change, fmt=str):
        super().__init__()
        self._on_change = on_change
        self._fmt = fmt
        self._boxes = {}  # value -> QCheckBox
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.addWidget(QtWidgets.QLabel(f'{title}:'))

    def sync(self, values):
        """Ensure a checkbox exists for each value (new ones default to checked)."""
        for v in values:
            if v not in self._boxes:
                cb = QtWidgets.QCheckBox(self._fmt(v))
                cb.setChecked(True)
                cb.stateChanged.connect(lambda _state: self._on_change())
                self._boxes[v] = cb
                self._layout.addWidget(cb)

    def selected(self):
        if not self._boxes:
            return None
        checked = {v for v, cb in self._boxes.items() if cb.isChecked()}
        return None if len(checked) == len(self._boxes) else checked


class LiveEstimWindow(QtWidgets.QMainWindow):
    """Control bar + a vertically-scrolling grid of pyqtgraph panels showing Plot 1."""

    def __init__(self, exp_conn, session_id):
        super().__init__()
        self.exp_conn = exp_conn
        self.session_id = session_id
        # Seed seen trials from what's already compiled so a restart doesn't redo the session.
        self.seen_starts = get_existing_trial_starts(session_id)
        self._has_drawn = False
        self.start_gen_id = START_GEN_ID

        # Grid state.
        self._grid_config = None          # (n_rows, tuple(col_keys)) — rebuilt only on change
        self.plots = {}                   # (row, col_key) -> PlotItem
        self.legends = {}                 # (row, col_key) -> LegendItem
        self.series = {}                  # (row, col_key, series_key) -> {'curve','label','base'}
        # Stable spec_id -> color: a spec keeps its color for the whole session and across
        # every panel, regardless of which other specs are present or when it first appears.
        self._spec_color = {}

        self._setup_ui()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self._refresh()  # initial compile + draw
        self.timer.start(self.interval_spin.value() * 1000)

    # ---- UI -------------------------------------------------------------
    def _setup_ui(self):
        self.setWindowTitle(f'Live EStim Analysis — {self.session_id}')
        self.setGeometry(100, 100, 1500, 1000)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Control bar — seed for future buttons/dropdowns.
        bar = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton('Refresh now')
        self.refresh_button.clicked.connect(self._force_refresh)

        self.live_checkbox = QtWidgets.QCheckBox('Live')
        self.live_checkbox.setChecked(True)
        self.live_checkbox.stateChanged.connect(self._toggle_live)

        self.interval_spin = QtWidgets.QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(DEFAULT_POLL_SECONDS)
        self.interval_spin.setSuffix(' s')
        self.interval_spin.valueChanged.connect(self._change_interval)

        self.status_label = QtWidgets.QLabel('Starting…')

        self.start_gen_spin = QtWidgets.QSpinBox()
        self.start_gen_spin.setRange(0, 1000000)
        self.start_gen_spin.setValue(self.start_gen_id)
        self.start_gen_spin.valueChanged.connect(self._on_start_gen_changed)

        bar.addWidget(self.refresh_button)
        bar.addWidget(self.live_checkbox)
        bar.addWidget(QtWidgets.QLabel('Poll every'))
        bar.addWidget(self.interval_spin)
        bar.addSpacing(16)
        bar.addWidget(QtWidgets.QLabel('Start gen'))
        bar.addWidget(self.start_gen_spin)
        bar.addStretch(1)
        bar.addWidget(self.status_label)
        layout.addLayout(bar)

        # Behavioral-parameter filters. Each re-renders (no recompile) on toggle. Checkboxes
        # are populated from the data as values appear; all-checked means no filtering.
        filt_bar = QtWidgets.QHBoxLayout()
        self.noise_filter = _MultiCheckFilter('Noise', self._rerender,
                                              fmt=lambda v: f'{float(v) * 100:.0f}%')
        self.type_filter = _MultiCheckFilter('Trial type', self._rerender)
        self.sl_filter = _MultiCheckFilter('Sample len', self._rerender, fmt=lambda v: f'{v}')
        filt_bar.addWidget(self.noise_filter)
        filt_bar.addSpacing(12)
        filt_bar.addWidget(self.type_filter)
        filt_bar.addSpacing(12)
        filt_bar.addWidget(self.sl_filter)
        filt_bar.addStretch(1)
        layout.addLayout(filt_bar)

        # Scrollable grid of panels.
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(_SCROLLBAR_OFF)
        self.grid_host = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.grid_host)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.grid_host)
        layout.addWidget(self.scroll)

    # ---- polling --------------------------------------------------------
    def _toggle_live(self):
        if self.live_checkbox.isChecked():
            self.timer.start(self.interval_spin.value() * 1000)
        else:
            self.timer.stop()

    def _change_interval(self, value):
        if self.live_checkbox.isChecked():
            self.timer.start(value * 1000)

    def _force_refresh(self):
        self._refresh(force=True)

    def _on_start_gen_changed(self, value):
        self.start_gen_id = value
        self._rerender()

    def _rerender(self):
        """Redraw from the already-compiled data (no DB poll). Used when start-gen or a filter
        changes — those only affect what we display, not what's compiled."""
        try:
            n_trials = self._update_plots()
            self._has_drawn = True
        except Exception as e:
            self.status_label.setText(f'Plot error: {e}')
            return
        self.status_label.setText(f'{self.session_id}: {n_trials} trials plotted')

    def _apply_filters(self, data):
        """Drop rows excluded by the behavioral-parameter filters."""
        df = data
        sel = self.noise_filter.selected()
        if sel is not None:
            df = df[df['NoiseChance'].isin(sel)]
        sel = self.type_filter.selected()
        if sel is not None:
            df = df[df['TrialType'].isin(sel)]
        sel = self.sl_filter.selected()
        if sel is not None:
            df = df[df['SampleLength'].isin(sel)]
        return df

    def _refresh(self, force=False):
        """Compile new trials, then update the curves only if something changed (or forced).
        Updating is in-place (setData), so it never disturbs scroll/zoom — but skipping the
        no-op case still avoids redundant DB reads."""
        try:
            n_new = compile_new_trials(self.exp_conn, self.session_id, self.seen_starts)
        except Exception as e:
            self.status_label.setText(f'Compile error: {e}')
            return

        if n_new == 0 and self._has_drawn and not force:
            return

        try:
            n_trials = self._update_plots()
            self._has_drawn = True
        except Exception as e:
            self.status_label.setText(f'Plot error: {e}')
            return

        suffix = f'  (+{n_new} new)' if n_new else ''
        self.status_label.setText(f'{self.session_id}: {n_trials} trials plotted{suffix}')

    # ---- plotting -------------------------------------------------------
    def _update_plots(self):
        """Recompute metric curves and push them into the existing pyqtgraph curves. Returns
        the number of plotted trials (after filtering)."""
        data_full = read_session_trials_as_exp_format(self.session_id, self.start_gen_id)
        if data_full is None or len(data_full) == 0:
            self.status_label.setText(f'{self.session_id}: waiting for trials…')
            return 0

        # Offer every available value in the filters (so deselected ones can be re-enabled),
        # then apply the current selection.
        self.noise_filter.sync(sorted(data_full['NoiseChance'].dropna().unique()))
        self.type_filter.sync([t for t in ('Hypothesized Shape', 'Delta Shape', 'Removed Trial')
                               if (data_full['TrialType'] == t).any()])
        self.sl_filter.sync(sorted(data_full['SampleLength'].dropna().unique(), key=float))

        data_exp = self._apply_filters(data_full)
        if len(data_exp) == 0:
            self.status_label.setText(f'{self.session_id}: 0 trials after filters')
            return 0

        partition = partition_estim_data(data_exp)
        rows = _rows_for(partition.include_removed)
        # Skip a column entirely when it has no data (e.g. its trial type was filtered out).
        cols = [c for c in _columns_for(partition) if (len(c[2]) + len(c[3])) > 0]
        if not cols:
            return 0
        self._ensure_grid(rows, cols)

        for r, (_row_title, kind) in enumerate(rows):
            for (col_key, _col_title, on_df, off_df, spec_ids) in cols:
                self._update_cell(r, col_key, kind, on_df, off_df, spec_ids)
        return len(data_exp)

    def _ensure_grid(self, rows, cols):
        """(Re)build the panel grid only when the row/column layout changes (e.g. the Removed
        column first appears). Rebuilds are rare, so they don't affect steady-state scrolling."""
        col_keys = tuple(c[0] for c in cols)
        config = (len(rows), col_keys)
        if config == self._grid_config:
            return

        # Tear down any existing grid.
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.plots, self.legends, self.series = {}, {}, {}
        self._grid_config = config

        for r, (row_title, _kind) in enumerate(rows):
            for c, (col_key, col_title, *_rest) in enumerate(cols):
                glw = _ScrollGraphicsLayout(self.scroll, background='w')
                glw.setFixedHeight(PLOT_HEIGHT)
                # Plot in col 0 (stretches); legend in a fixed-width col 1 to its right, so the
                # legend never overlaps the data.
                pi = glw.addPlot(row=0, col=0)
                legend = pg.LegendItem(offset=(10, 10))
                glw.addItem(legend, row=0, col=1)
                glw.ci.layout.setColumnStretchFactor(0, 1)
                glw.ci.layout.setColumnFixedWidth(1, LEGEND_WIDTH)

                pi.setTitle(f'{row_title}: {col_title}')
                pi.showGrid(x=True, y=True, alpha=0.3)
                pi.setLabel('left', '%')
                pi.setLabel('bottom', 'Noise Chance (%)')
                vb = pi.getViewBox()
                vb.invertX(True)  # higher noise on the left, matching the batch plot
                # Fixed ranges + no autorange so live updates never move the user's view.
                # Clamp y to [0, 100] so the plot can never show values outside that range.
                vb.setRange(xRange=(-5, 105), yRange=(0, 100), padding=0)
                vb.setLimits(yMin=0, yMax=100)
                vb.disableAutoRange()
                self.grid_layout.addWidget(glw, r, c)
                self.plots[(r, col_key)] = pi
                self.legends[(r, col_key)] = legend

    def _color_for_spec(self, spec):
        """Return this spec's stable color, assigning the next palette entry on first sight."""
        spec = int(spec)
        if spec not in self._spec_color:
            self._spec_color[spec] = _SPEC_COLORS[len(self._spec_color) % len(_SPEC_COLORS)]
        return self._spec_color[spec]

    def _update_cell(self, row, col_key, kind, on_df, off_df, spec_ids):
        plot = self.plots[(row, col_key)]
        legend = self.legends[(row, col_key)]

        # Series to show in this cell: EStim OFF (black dashed) + one per spec (colored).
        wanted = {'OFF': (off_df, 'EStim OFF', pg.mkPen('k', width=2, style=_DASH_LINE), (0, 0, 0))}
        for spec in sorted(spec_ids):
            color = self._color_for_spec(spec)
            wanted[('spec', spec)] = (on_df[on_df['EStimSpecId'] == spec],
                                      f'Spec {int(spec)}', pg.mkPen(color, width=2), color)

        for series_key, (df, base, pen, color) in wanted.items():
            xs, ys, ns = curve_points(df, kind)
            sid = (row, col_key, series_key)
            if sid not in self.series:
                curve = plot.plot([], [], pen=pen, symbol='o', symbolSize=6,
                                  symbolBrush=color, symbolPen=color)
                legend.addItem(curve, base)
                # Hold the legend LabelItem so we can update the n-count in place.
                label = legend.items[-1][1] if legend.items else None
                self.series[sid] = {'curve': curve, 'label': label, 'base': base}
            entry = self.series[sid]
            entry['curve'].setData(xs, ys)
            if entry['label'] is not None:
                entry['label'].setText(f"{entry['base']} (n={int(sum(ns))})")
            self._sync_point_labels(plot, entry, xs, ys, ns, color)

        # Drop series no longer present (e.g. a spec that disappeared after filtering).
        for sid in [s for s in self.series if s[0] == row and s[1] == col_key and s[2] not in wanted]:
            entry = self.series.pop(sid)
            plot.removeItem(entry['curve'])
            for t in entry.get('texts', []):
                plot.removeItem(t)
            try:
                legend.removeItem(entry['curve'])
            except Exception:
                pass

    def _sync_point_labels(self, plot, entry, xs, ys, ns, color):
        """Show the per-point sample size (n) as text above each data point (below it near the
        top, so labels stay inside the 0–100 view)."""
        texts = entry.setdefault('texts', [])
        while len(texts) < len(xs):
            t = pg.TextItem(anchor=(0.5, 1.0), color=color)
            plot.addItem(t)
            texts.append(t)
        while len(texts) > len(xs):
            plot.removeItem(texts.pop())
        for t, x, y, n in zip(texts, xs, ys, ns):
            t.setText(str(int(n)))
            t.setPos(x, y)
            try:
                t.setAnchor((0.5, 1.0) if y <= 85 else (0.5, 0.0))
            except Exception:
                pass


def main():
    ensure_estimshape_trials_table()
    exp_conn = Connection(context.nafc_database)
    session_id, _ = read_session_id_and_date_from_db_name(context.nafc_database)

    app = QtWidgets.QApplication(sys.argv)
    window = LiveEstimWindow(exp_conn, session_id)
    window.show()
    # PyQt6/PySide6 use exec(); PyQt5 uses exec_().
    run = app.exec if hasattr(app, 'exec') else app.exec_
    sys.exit(run())


if __name__ == '__main__':
    main()

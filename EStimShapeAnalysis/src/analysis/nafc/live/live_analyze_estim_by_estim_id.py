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
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

from clat.util.connection import Connection
from src.startup import context
from src.repository.export_to_repository import read_session_id_and_date_from_db_name

from src.analysis.nafc.analyze_estim_by_estim_id import partition_estim_data
from src.analysis.nafc.live.live_estim_compile import (
    REPO_DB, ensure_estimshape_trials_table, compile_new_trials, get_existing_trial_starts,
)
from src.analysis.nafc.live.upcoming_trials import (
    read_upcoming_trials, group_upcoming_counts, task_ids_for_group, delete_upcoming_tasks,
    GROUP_DIMENSIONS, DEFAULT_GROUP_DIMENSIONS,
)
from src.analysis.nafc.live.live_stats import run_session_stats, METRICS as STATS_METRICS
from src.analysis.nafc import bias_analysis as bias

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_POLL_SECONDS = 5
START_GEN_ID = 1                 # keep start_gen_id; trials below this are not plotted
PLOT_HEIGHT = 300                # px per panel; the column of panels scrolls vertically
RECENT_TRIALS_N = 5              # how many most-recent trials to summarize under the status
# Experimental stim types that make up Plot 1 (matches analyze_estim_by_estim_id.main).
_EXPERIMENTAL_STIM_TYPES = ['EStimShapeVariantsDeltaNAFCStim', 'EStimShapeVariantsDeletedNAFCStim',
                            'EStimShapeSplitTextureNAFCStim']

# (row_title, metric_kind) for the metric rows; the removed row is appended when relevant.
_BASE_ROWS = [
    ('% Hypothesized vs Delta',  'hyp_vs_delta'),
    ('% Hypothesized',           'hypothesized'),
    ('% Correct',                'correct'),
    ('% Rand Choice',            'rand'),
]
_REMOVED_ROW = ('% Removed Choice', 'removed')

# tab10-ish palette for per-spec curves; EStim OFF is always black/dashed.
_SPEC_COLORS = [
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189),
    (140, 86, 75), (227, 119, 194), (127, 127, 127), (188, 189, 34), (23, 190, 207),
]

# Sliding-window tab.
WINDOW_SIZE = 50          # trials per window
WINDOW_STEP = 5           # window stride (trials)
WINDOW_PLOT_HEIGHT = 440  # px per sliding-window panel
WINDOW_METRIC = 'hyp_vs_delta'   # effect size uses % hypothesized vs delta
# Behavioral parameters the sliding window conditions on, in addition to trial type and estim
# spec. Each distinct combination present in the data becomes its own line (effect-size panels
# and the no-estim % correct baseline alike), distinguished by pen style with the values spelled
# out in the legend; noise additionally drives line alpha as a secondary cue. Only columns that
# exist in the data are used, so this degrades gracefully on sessions missing the newer columns.
_WINDOW_COND_COLS = ['NoiseChance', 'NumChoices', 'NumProceduralDistractors', 'NumRandDistractors']
_WINDOW_COMBO_FMT = {
    'NoiseChance':              lambda v: f'{float(v) * 100:.0f}%',
    'NumChoices':               lambda v: f'{int(float(v))}ch',
    'NumProceduralDistractors': lambda v: f'{int(float(v))}proc',
    'NumRandDistractors':       lambda v: f'{int(float(v))}rand',
}
_TRIAL_TYPE_ORDER = ('Hypothesized Shape', 'Delta Shape', 'Removed Trial')
# Behavioral (catch/training) trials: kept out of the estim analysis but shown in the
# sliding-window % correct baseline, like analyze_estim_by_condition's sliding window.
_BEHAVIORAL_STIM_TYPE = 'EStimShapeProceduralBehavioralStim'
_ALL_TRIAL_TYPES = ('Hypothesized Shape', 'Delta Shape', 'Removed Trial', 'Behavioral')
# Colors for the no-estim % correct baseline lines (one per trial type + Combined).
_BASELINE_COLORS = {
    'Hypothesized Shape': (31, 119, 180),
    'Delta Shape':        (214, 39, 40),
    'Removed Trial':      (140, 86, 75),
    'Behavioral':         (44, 160, 44),
    'Combined':           (0, 0, 0),
}
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
_EDIT_ROLE = _qt_enum('ItemDataRole', 'EditRole')
_USER_ROLE = _qt_enum('ItemDataRole', 'UserRole')
_KEEP_ASPECT = _qt_enum('AspectRatioMode', 'KeepAspectRatio')
_SMOOTH_TRANSFORM = _qt_enum('TransformationMode', 'SmoothTransformation')
_ALIGN_CENTER = _qt_enum('AlignmentFlag', 'AlignCenter')

# Bias tab geometry.
BIAS_ROW_HEIGHT = 260      # px per group row
BIAS_THUMB_PX = 76         # thumbnail edge length


def _scoped_enum(cls, member):
    """Resolve a Qt widget enum value across bindings: PyQt5 exposes them flat on the class
    (QMessageBox.Yes, QAbstractItemView.NoEditTriggers), while PyQt6/PySide6 scope them under
    a nested enum class (QMessageBox.StandardButton.Yes, QAbstractItemView.SelectionBehavior.
    SelectRows). Try the flat form first, then search nested enum classes."""
    if hasattr(cls, member):
        return getattr(cls, member)
    for name in dir(cls):
        sub = getattr(cls, name)
        if isinstance(sub, type) and hasattr(sub, member):
            return getattr(sub, member)
    raise AttributeError(f'{cls.__name__} has no enum member {member!r}')


_NO_EDIT_TRIGGERS = _scoped_enum(QtWidgets.QAbstractItemView, 'NoEditTriggers')
_SELECT_ROWS = _scoped_enum(QtWidgets.QAbstractItemView, 'SelectRows')
_MSG_YES = _scoped_enum(QtWidgets.QMessageBox, 'Yes')
# Pen styles used to distinguish noise levels within a spec in the sliding-window tab
# (alpha alone was too subtle). Assigned per noise value, stable for the session.
_NOISE_STYLES = [_qt_enum('PenStyle', name) for name in
                 ('SolidLine', 'DashLine', 'DotLine', 'DashDotLine', 'DashDotDotLine')]


def read_session_trials_as_exp_format(session_id, start_gen_id=START_GEN_ID,
                                      max_gen_id=None, include_behavioral=False):
    """Read this session's rows from EStimShapeTrials and map them back to the experiment-DB
    column names the partitioning expects. Applies the start_gen_id cut (and the max_gen_id cut
    when given; None means no upper bound) and restricts to experimental stim types (plus
    behavioral trials when include_behavioral, for the sliding-window % correct baseline)."""
    conn = Connection(REPO_DB)
    conn.execute("""
        SELECT task_id, estim_spec_id, is_estim_on, is_hypothesized_choice,
               is_correct_choice, trial_type, noise_chance, base_mstick_id,
               gen_id, trial_start, sample_length, trial_class, choice,
               is_texture_split, split_render_is_sample, inverted_shading,
               contrast_texture, is_3d_choice,
               num_choices, num_procedural_distractors, num_rand_distractors
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
    # Split-texture columns; NULL/None for non-split trials. Kept nullable (no astype(bool)) so
    # the split panel can select split trials and the others stay out of its denominators.
    out['IsTextureSplit']      = db['is_texture_split'].fillna(0).astype(bool)
    out['SplitRenderIsSample'] = db['split_render_is_sample']
    out['InvertedShading']     = db['inverted_shading']
    out['ContrastTexture']     = db['contrast_texture']
    out['Is3DChoice']          = db['is_3d_choice']
    # Behavioral choice-set parameters (nullable; not every trial records them).
    out['NumChoices']              = db['num_choices']
    out['NumProceduralDistractors'] = db['num_procedural_distractors']
    out['NumRandDistractors']      = db['num_rand_distractors']
    # Use the compiled trial-type label directly so 'Behavioral' survives (deriving it from
    # IsDelta/IsRemovedTrial would mislabel behavioral trials as 'Hypothesized Shape').
    out['TrialType'] = db['trial_type']

    out = out[out['GenId'] >= start_gen_id]
    if max_gen_id is not None:
        out = out[out['GenId'] <= max_gen_id]
    allowed = list(_EXPERIMENTAL_STIM_TYPES)
    if include_behavioral:
        allowed.append(_BEHAVIORAL_STIM_TYPE)
    out = out[out['StimType'].isin(allowed)]
    return out


def _recent_trial_type_label(trial_type, is_texture_split):
    """Trial-type label for the recent-trials summary, marking split-texture trials so they're
    distinguishable from ordinary ones (e.g. 'Hypothesized Split Texture')."""
    if not is_texture_split:
        return trial_type
    if trial_type == 'Hypothesized Shape':
        return 'Hypothesized Split Texture'
    if trial_type == 'Delta Shape':
        return 'Delta Split Texture'
    # Any other base type (Removed Trial, Behavioral, …): just flag the split treatment.
    return f'{trial_type} (Split Texture)'


def read_recent_trials(session_id, n=RECENT_TRIALS_N):
    """Return a short text summary of the n most-recent trials (newest first): trial type
    (split-texture trials are labelled as such), estim spec id (or 'no estim'), and noise
    level. Independent of tab/filters."""
    conn = Connection(REPO_DB)
    conn.execute("""
        SELECT trial_type, is_estim_on, estim_spec_id, noise_chance, is_texture_split
        FROM EStimShapeTrials
        WHERE session_id = %s
        ORDER BY task_id DESC
        LIMIT %s
    """, (session_id, n))
    rows = conn.fetch_all()
    lines = []
    for trial_type, is_estim_on, spec, noise, is_texture_split in rows:
        label = _recent_trial_type_label(trial_type, bool(is_texture_split))
        estim = f'spec {int(spec)}' if (is_estim_on and spec is not None) else 'no estim'
        noise_s = f'{float(noise) * 100:.0f}%' if noise is not None else 'n/a'
        lines.append(f'{label}  |  {estim}  |  noise {noise_s}')
    return lines


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
    if kind == 'pct_3d':
        # Split-texture trials only: among match-vs-foil picks (Is3DChoice non-null), the
        # fraction that chose the option whose hypothesized limb was rendered in 3D.
        d = df[df['Is3DChoice'].notna()]
        return d, d['Is3DChoice'].astype(bool)
    if kind == 'rand':
        return df, (df['Choice'] == 'rand')
    if kind == 'removed':
        return df, ((df['Choice'] == 'removed') |
                    ((df['IsRemovedTrial'] == True) & (df['Choice'] == 'match')))
    if kind == 'correct':
        # % chose the match (the rewarded option), over all trials in the group.
        return df, df['IsCorrect'].astype(bool)
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


def _alpha_for_noise(noise):
    """Map a noise chance (0..1) to a line alpha — higher noise = more opaque. Kept fairly
    high so lines stay visible; line style (not alpha) is the primary noise distinguisher."""
    return max(0.55, min(1.0, 0.55 + 0.45 * float(noise)))


def _norm_combo_val(v):
    """Normalize a grouping value for use as a stable dict key: numeric -> float (NaN -> None),
    everything else unchanged. Avoids NaN!=NaN churn when keying lines on behavioral combos."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return v


def _window_cond_cols(data):
    """The subset of _WINDOW_COND_COLS actually present in this data (always includes the ones
    that exist; older sessions missing the newer columns just condition on fewer params)."""
    if data is None:
        return []
    return [c for c in _WINDOW_COND_COLS if c in data.columns]


def _format_window_combo(cond_cols, combo):
    """Legend text for a behavioral combo, e.g. '50% 4ch 1proc 2rand'. None values (param not
    recorded for that line) are skipped; an all-None combo renders as 'all'."""
    parts = []
    for col, v in zip(cond_cols, combo):
        if v is None:
            continue
        parts.append(_WINDOW_COMBO_FMT.get(col, str)(v))
    return ' '.join(parts) if parts else 'all'


def _combo_value(cond_cols, combo, name):
    """Pull one named param's value out of a combo tuple (None if absent)."""
    if name in cond_cols:
        i = cond_cols.index(name)
        if i < len(combo):
            return combo[i]
    return None


def _combo_sort_key(combo):
    """Type-safe sort key for a combo tuple that may mix None and floats."""
    return tuple((v is None, str(v)) for v in combo)


def sliding_window_series(data, window_size=WINDOW_SIZE, step=WINDOW_STEP, kind=WINDOW_METRIC,
                          cond_cols=None):
    """Compute sliding-window effect-size traces, conditioned on behavioral params AND spec.

    For each window (a contiguous block of trials in task order) and each condition
    (trial_type, behavioral combo, estim_spec_id), effect = estim_on %metric − estim_off %metric,
    where the OFF baseline is matched on (trial_type, behavioral combo). The behavioral combo is
    the values of ``cond_cols`` (noise plus the choice-set params: # choices, # procedural and
    # random distractors). The metric (default % hypothesized vs delta) drops rand/removed
    choices before averaging.

    Returns {trial_type: {(spec_id, combo): (xs, ys)}} with combo a tuple aligned to cond_cols
    and xs = window-center trial index.
    """
    out = {}
    if data is None or len(data) == 0:
        return out
    if cond_cols is None:
        cond_cols = _window_cond_cols(data)
    data = data.reset_index(drop=True)
    n = len(data)
    for start in range(0, max(n - window_size, 0) + 1, step):
        w = data.iloc[start:start + window_size]
        center = start + window_size // 2
        d, vals = _metric_series(w, kind)
        if len(d) == 0:
            continue
        work = d.assign(_v=np.asarray(vals, dtype=float))
        on = work[work['EStimEnabled'] == True].dropna(subset=['EStimSpecId'])
        off = work[work['EStimEnabled'] == False]
        if len(on) == 0 or len(off) == 0:
            continue
        off_pct = off.groupby(['TrialType', *cond_cols], dropna=False)['_v'].mean() * 100.0
        on_pct = on.groupby(['TrialType', *cond_cols, 'EStimSpecId'], dropna=False)['_v'].mean() * 100.0
        # Normalized (trial_type, combo) -> baseline %; sidesteps NaN-in-MultiIndex lookups.
        off_map = {}
        for okey, v in off_pct.items():
            okey = okey if isinstance(okey, tuple) else (okey,)
            off_map[(okey[0], tuple(_norm_combo_val(x) for x in okey[1:]))] = v
        for okey, pct_on in on_pct.items():
            okey = okey if isinstance(okey, tuple) else (okey,)
            tt = okey[0]
            combo = tuple(_norm_combo_val(x) for x in okey[1:1 + len(cond_cols)])
            spec = okey[-1]
            base = off_map.get((tt, combo))
            if base is None:
                continue
            xs, ys = out.setdefault(tt, {}).setdefault((int(spec), combo), ([], []))
            xs.append(center)
            ys.append(pct_on - base)
    return out


def sliding_window_baseline(data, window_size=WINDOW_SIZE, step=WINDOW_STEP, cond_cols=None):
    """Per-window % correct of NO-ESTIM trials, split by trial type AND behavioral combo
    (+ a pooled Combined) — the baseline panel from analyze_estim_by_condition's sliding window.
    Behavioral trials are included.

    Returns {(trial_type, combo): (xs, ys)} with combo aligned to cond_cols; the pooled line is
    keyed ('Combined', ()). xs = window-center trial index, ys = % correct.
    """
    out = {}
    if data is None or len(data) == 0:
        return out
    if cond_cols is None:
        cond_cols = _window_cond_cols(data)
    data = data.reset_index(drop=True)
    n = len(data)
    for start in range(0, max(n - window_size, 0) + 1, step):
        w = data.iloc[start:start + window_size]
        center = start + window_size // 2
        off = w[w['EStimEnabled'] == False]
        if len(off) == 0:
            continue
        for gkey, sub in off.groupby(['TrialType', *cond_cols], dropna=False):
            gkey = gkey if isinstance(gkey, tuple) else (gkey,)
            tt = gkey[0]
            combo = tuple(_norm_combo_val(x) for x in gkey[1:])
            vals = sub['IsCorrect'].dropna()
            if len(vals) > 0:
                xs, ys = out.setdefault((tt, combo), ([], []))
                xs.append(center)
                ys.append(float(vals.mean()) * 100.0)
        combined = off['IsCorrect'].dropna()
        if len(combined) > 0:
            xs, ys = out.setdefault(('Combined', ()), ([], []))
            xs.append(center)
            ys.append(float(combined.mean()) * 100.0)
    return out


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

    def __init__(self, exp_conn, session_id, session_date=None):
        super().__init__()
        self.exp_conn = exp_conn
        self.session_date = session_date
        self.session_id = session_id
        # Seed seen trials from what's already compiled so a restart doesn't redo the session.
        self.seen_starts = get_existing_trial_starts(session_id)
        self._has_drawn = False
        self.start_gen_id = START_GEN_ID
        self.max_gen_id = None   # None = no upper bound (default)

        # Overview-tab grid state.
        self._grid_config = None          # (n_rows, tuple(col_keys)) — rebuilt only on change
        self.plots = {}                   # (row, col_key) -> PlotItem
        self.legends = {}                 # (row, col_key) -> LegendItem
        self.series = {}                  # (row, col_key, series_key) -> {'curve','label','base'}

        # Sliding-window-tab grid state (columns = trial types).
        self._win_config = None           # tuple(trial_types) — rebuilt only on change
        self.win_plots = {}               # trial_type -> PlotItem
        self.win_legends = {}             # trial_type -> LegendItem
        self.win_series = {}              # (trial_type, spec, noise) -> {'curve','label'}

        # Texture-split-tab grid state (rows = split/inverted combos, columns = variant/delta).
        self._split_grid_config = None    # (tuple(row_keys), tuple(col_keys)) — rebuilt on change
        self.split_plots = {}             # (row_key, col_key) -> PlotItem
        self.split_legends = {}           # (row_key, col_key) -> LegendItem
        self.split_series = {}            # (row_key, col_key, series_key) -> {'curve','label','base'}

        # Bias-tab grid state (rows = lineage groups; columns = thumbnails / bars / time series).
        self._bias_config = None           # tuple of (variant_id, tuple(member_ids)) — rebuilt on change
        self.bias_bar_plots = {}           # variant_id -> PlotItem (bar chart)
        self.bias_ts_plots = {}            # variant_id -> PlotItem (time series)
        self.bias_ts_legends = {}          # variant_id -> LegendItem
        self.bias_bar_items = {}           # variant_id -> BarGraphItem (replaced each update)
        self.bias_ts_series = {}           # (variant_id, sample_id, picked_id) -> curve

        # Upcoming-trials-tab state: which grouping dimensions are checked, plus the last-read
        # trials/grouping so a delete can map a selected row back to its task_ids.
        self.upcoming_checks = {}          # column -> QCheckBox
        self._upcoming_df = None
        self._upcoming_group_dims = []

        # Stats-tab state. Runs only on explicit button press (never on the poll timer).
        self._stats_result = None

        # Stable spec_id -> color: a spec keeps its color for the whole session and across
        # every panel, regardless of which other specs are present or when it first appears.
        self._spec_color = {}
        # Stable noise -> pen style for the sliding-window tab (noise distinguisher).
        self._noise_style = {}
        # Stable behavioral-combo -> pen style for the sliding-window tab, shared between the
        # effect-size panels and the % correct baseline so the same combo looks the same in both.
        self._combo_style = {}

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

        # Max gen: the minimum value (-1) is shown as 'No max' and means no upper bound (default),
        # so there's always an "infinite" option. Any value >= 0 caps trials at that generation.
        self.max_gen_spin = QtWidgets.QSpinBox()
        self.max_gen_spin.setRange(-1, 1000000)
        self.max_gen_spin.setSpecialValueText('No max')
        self.max_gen_spin.setValue(-1)
        self.max_gen_spin.valueChanged.connect(self._on_max_gen_changed)

        bar.addWidget(self.refresh_button)
        bar.addWidget(self.live_checkbox)
        bar.addWidget(QtWidgets.QLabel('Poll every'))
        bar.addWidget(self.interval_spin)
        bar.addSpacing(16)
        bar.addWidget(QtWidgets.QLabel('Start gen'))
        bar.addWidget(self.start_gen_spin)
        bar.addSpacing(8)
        bar.addWidget(QtWidgets.QLabel('Max gen'))
        bar.addWidget(self.max_gen_spin)
        bar.addStretch(1)
        bar.addWidget(self.status_label)
        layout.addLayout(bar)

        # Summary of the most-recent trials, shown just under the status line.
        self.recent_label = QtWidgets.QLabel('')
        self.recent_label.setStyleSheet('color: #444;')
        font = self.recent_label.font()
        font.setFamily('monospace')
        self.recent_label.setFont(font)
        layout.addWidget(self.recent_label)

        # Behavioral-parameter filters. Each re-renders (no recompile) on toggle. Checkboxes
        # are populated from the data as values appear; all-checked means no filtering.
        filt_bar = QtWidgets.QHBoxLayout()
        self.noise_filter = _MultiCheckFilter('Noise', self._rerender,
                                              fmt=lambda v: f'{float(v) * 100:.0f}%')
        self.type_filter = _MultiCheckFilter('Trial type', self._rerender)
        self.sl_filter = _MultiCheckFilter('Sample len', self._rerender, fmt=lambda v: f'{v}')
        # Behavioral choice-set parameter filters (mirror the by-condition behavioral keys).
        _int_fmt = lambda v: f'{int(float(v))}'
        self.nchoices_filter = _MultiCheckFilter('# Choices', self._rerender, fmt=_int_fmt)
        self.nproc_filter = _MultiCheckFilter('# Proc', self._rerender, fmt=_int_fmt)
        self.nrand_filter = _MultiCheckFilter('# Rand', self._rerender, fmt=_int_fmt)
        filt_bar.addWidget(self.noise_filter)
        filt_bar.addSpacing(12)
        filt_bar.addWidget(self.type_filter)
        filt_bar.addSpacing(12)
        filt_bar.addWidget(self.sl_filter)
        filt_bar.addSpacing(12)
        filt_bar.addWidget(self.nchoices_filter)
        filt_bar.addSpacing(12)
        filt_bar.addWidget(self.nproc_filter)
        filt_bar.addSpacing(12)
        filt_bar.addWidget(self.nrand_filter)
        filt_bar.addStretch(1)
        layout.addLayout(filt_bar)

        # Tabs: Overview (Plot 1) and Sliding Window. Both share the control bar/filters above.
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # Overview tab — vertically-scrolling grid of metric x trial-type panels.
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(_SCROLLBAR_OFF)
        self.grid_host = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.grid_host)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.grid_host)
        self.tabs.addTab(self.scroll, 'Overview')

        # Sliding-window tab — one effect-size panel per trial type (columns).
        self.win_scroll = QtWidgets.QScrollArea()
        self.win_scroll.setWidgetResizable(True)
        self.win_scroll.setHorizontalScrollBarPolicy(_SCROLLBAR_OFF)
        self.win_host = QtWidgets.QWidget()
        self.win_grid_layout = QtWidgets.QGridLayout(self.win_host)
        self.win_grid_layout.setContentsMargins(4, 4, 4, 4)
        self.win_scroll.setWidget(self.win_host)
        self.tabs.addTab(self.win_scroll, 'Sliding Window')

        # Texture Split tab — % 3D grid (rows = split/inverted combos, columns = variant/delta).
        # The combine toggles live here because they only affect this tab's row layout.
        self.split_tab = QtWidgets.QWidget()
        split_tab_layout = QtWidgets.QVBoxLayout(self.split_tab)
        split_ctrl = QtWidgets.QHBoxLayout()
        self.combine_sample_cb = QtWidgets.QCheckBox('Combine sample/foil')
        self.combine_sample_cb.stateChanged.connect(lambda _s: self._rerender())
        self.combine_inverted_cb = QtWidgets.QCheckBox('Combine normal/inverted')
        self.combine_inverted_cb.stateChanged.connect(lambda _s: self._rerender())
        split_ctrl.addWidget(self.combine_sample_cb)
        split_ctrl.addWidget(self.combine_inverted_cb)
        split_ctrl.addStretch(1)
        split_tab_layout.addLayout(split_ctrl)

        self.split_scroll = QtWidgets.QScrollArea()
        self.split_scroll.setWidgetResizable(True)
        self.split_scroll.setHorizontalScrollBarPolicy(_SCROLLBAR_OFF)
        self.split_host = QtWidgets.QWidget()
        self.split_grid_layout = QtWidgets.QGridLayout(self.split_host)
        self.split_grid_layout.setContentsMargins(4, 4, 4, 4)
        self.split_scroll.setWidget(self.split_host)
        split_tab_layout.addWidget(self.split_scroll)
        self.tabs.addTab(self.split_tab, 'Texture Split')

        # Bias tab — one row per lineage group (variant + its deltas). Col 0: member thumbnails
        # with colour-coded borders (the legend); col 1: per-sample pick distribution bars
        # (coloured by which member was picked); col 2: the sliding-window version. Estim-off
        # (behavioural) variant/delta trials only; honours the start/max-gen filters.
        self.bias_scroll = QtWidgets.QScrollArea()
        self.bias_scroll.setWidgetResizable(True)
        self.bias_host = QtWidgets.QWidget()
        self.bias_grid_layout = QtWidgets.QGridLayout(self.bias_host)
        self.bias_grid_layout.setContentsMargins(4, 4, 4, 4)
        self.bias_scroll.setWidget(self.bias_host)
        self.tabs.addTab(self.bias_scroll, 'Bias')

        # Upcoming Trials tab — counts of queued-but-not-yet-run trials (TaskToDo minus
        # TaskDone), grouped by the dimensions the user checks. Independent of the
        # completed-trial filters/start-gen above (those describe trials that already ran).
        self.upcoming_tab = QtWidgets.QWidget()
        upcoming_layout = QtWidgets.QVBoxLayout(self.upcoming_tab)

        group_bar = QtWidgets.QHBoxLayout()
        group_bar.addWidget(QtWidgets.QLabel('Group by:'))
        for col, label in GROUP_DIMENSIONS:
            cb = QtWidgets.QCheckBox(label)
            cb.setChecked(col in DEFAULT_GROUP_DIMENSIONS)
            cb.stateChanged.connect(lambda _s: self._render_upcoming())
            self.upcoming_checks[col] = cb
            group_bar.addWidget(cb)
        group_bar.addStretch(1)
        self.upcoming_total_label = QtWidgets.QLabel('')
        group_bar.addWidget(self.upcoming_total_label)
        upcoming_layout.addLayout(group_bar)

        self.upcoming_table = QtWidgets.QTableWidget()
        self.upcoming_table.setEditTriggers(_NO_EDIT_TRIGGERS)
        self.upcoming_table.setSortingEnabled(True)
        self.upcoming_table.setSelectionBehavior(_SELECT_ROWS)
        upcoming_layout.addWidget(self.upcoming_table)

        # Delete-by-group control: removes the queued trials in the selected group(s) from
        # TaskToDo (after a confirmation showing the exact count).
        delete_bar = QtWidgets.QHBoxLayout()
        delete_bar.addStretch(1)
        self.delete_upcoming_button = QtWidgets.QPushButton('Delete selected group(s)')
        self.delete_upcoming_button.clicked.connect(self._delete_selected_upcoming)
        delete_bar.addWidget(self.delete_upcoming_button)
        upcoming_layout.addLayout(delete_bar)
        self.tabs.addTab(self.upcoming_tab, 'Upcoming Trials')

        # Stats tab — runs analyze_estim_by_condition + permutation tests for THIS session
        # (persisting to the repository) and visualizes the single-session max-stat and
        # exceedance-count tests. Runs only when the button is pressed, never on the timer.
        self._build_stats_tab()

        # Render the newly-shown tab so it reflects the latest data/filters.
        self.tabs.currentChanged.connect(lambda _idx: self._rerender())

    def _build_stats_tab(self):
        self.stats_tab = QtWidgets.QWidget()
        stats_layout = QtWidgets.QVBoxLayout(self.stats_tab)

        ctrl = QtWidgets.QHBoxLayout()
        ctrl.addWidget(QtWidgets.QLabel('Metric:'))
        self.stats_metric_combo = QtWidgets.QComboBox()
        for value, label in STATS_METRICS:
            self.stats_metric_combo.addItem(label, value)
        ctrl.addWidget(self.stats_metric_combo)

        self.stats_studentize_cb = QtWidgets.QCheckBox('Studentize')
        ctrl.addWidget(self.stats_studentize_cb)

        ctrl.addWidget(QtWidgets.QLabel('Min trials/group:'))
        self.stats_min_trials_spin = QtWidgets.QSpinBox()
        self.stats_min_trials_spin.setRange(1, 1000)
        self.stats_min_trials_spin.setValue(15)
        ctrl.addWidget(self.stats_min_trials_spin)

        ctrl.addWidget(QtWidgets.QLabel('Permutations:'))
        self.stats_nperm_spin = QtWidgets.QSpinBox()
        self.stats_nperm_spin.setRange(100, 100000)
        self.stats_nperm_spin.setSingleStep(1000)
        self.stats_nperm_spin.setValue(1000)
        ctrl.addWidget(self.stats_nperm_spin)

        self.stats_run_button = QtWidgets.QPushButton('Run stats')
        self.stats_run_button.clicked.connect(self._run_stats)
        ctrl.addWidget(self.stats_run_button)
        ctrl.addStretch(1)
        self.stats_status_label = QtWidgets.QLabel('Not run yet.')
        ctrl.addWidget(self.stats_status_label)
        stats_layout.addLayout(ctrl)

        # Two stacked pyqtgraph panels: max-stat bar chart (top) and exceedance test (bottom).
        self.stats_maxstat_plot = pg.PlotWidget()
        self.stats_maxstat_plot.setBackground('w')
        self.stats_exceed_plot = pg.PlotWidget()
        self.stats_exceed_plot.setBackground('w')
        stats_layout.addWidget(self.stats_maxstat_plot)
        stats_layout.addWidget(self.stats_exceed_plot)

        self.tabs.addTab(self.stats_tab, 'Stats')

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

    def _on_max_gen_changed(self, value):
        # The spin's minimum (-1, shown as 'No max') means no upper bound.
        self.max_gen_id = None if value < 0 else value
        self._rerender()

    def _rerender(self):
        """Redraw from the already-compiled data (no DB poll). Used when start-gen or a filter
        changes — those only affect what we display, not what's compiled."""
        try:
            n_trials = self._update_active()
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
        sel = self.nchoices_filter.selected()
        if sel is not None:
            df = df[df['NumChoices'].isin(sel)]
        sel = self.nproc_filter.selected()
        if sel is not None:
            df = df[df['NumProceduralDistractors'].isin(sel)]
        sel = self.nrand_filter.selected()
        if sel is not None:
            df = df[df['NumRandDistractors'].isin(sel)]
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

        # The upcoming-trials tab also changes when a new generation is queued (which adds
        # TaskToDo rows without completing anything), so don't skip its redraw on "no new
        # completed trials".
        upcoming_active = self.tabs.currentWidget() is self.upcoming_tab
        if n_new == 0 and self._has_drawn and not force and not upcoming_active:
            return

        try:
            n_trials = self._update_active()
            self._has_drawn = True
        except Exception as e:
            self.status_label.setText(f'Plot error: {e}')
            return

        suffix = f'  (+{n_new} new)' if n_new else ''
        self.status_label.setText(f'{self.session_id}: {n_trials} trials plotted{suffix}')

    # ---- plotting -------------------------------------------------------
    def _read_and_filter(self, include_behavioral=False):
        """Read this session's compiled trials, refresh the filter choices, and apply them.
        Returns the filtered experiment-format DataFrame, or None when there is nothing to
        plot (status label is set accordingly). include_behavioral also pulls behavioral
        trials in (for the sliding-window % correct baseline)."""
        data_full = read_session_trials_as_exp_format(
            self.session_id, self.start_gen_id, self.max_gen_id,
            include_behavioral=include_behavioral)
        if data_full is None or len(data_full) == 0:
            self.status_label.setText(f'{self.session_id}: waiting for trials…')
            return None

        # Offer every available value in the filters (so deselected ones can be re-enabled),
        # then apply the current selection.
        self.noise_filter.sync(sorted(data_full['NoiseChance'].dropna().unique()))
        self.type_filter.sync([t for t in _ALL_TRIAL_TYPES if (data_full['TrialType'] == t).any()])
        self.sl_filter.sync(sorted(data_full['SampleLength'].dropna().unique(), key=float))
        self.nchoices_filter.sync(sorted(data_full['NumChoices'].dropna().unique(), key=float))
        self.nproc_filter.sync(sorted(data_full['NumProceduralDistractors'].dropna().unique(), key=float))
        self.nrand_filter.sync(sorted(data_full['NumRandDistractors'].dropna().unique(), key=float))

        data_exp = self._apply_filters(data_full)
        if len(data_exp) == 0:
            self.status_label.setText(f'{self.session_id}: 0 trials after filters')
            return None
        return data_exp

    def _update_recent_label(self):
        """Refresh the most-recent-trials summary under the status line."""
        try:
            lines = read_recent_trials(self.session_id, RECENT_TRIALS_N)
        except Exception:
            return
        header = f'Last {len(lines)} trials (newest first):'
        self.recent_label.setText('\n'.join([header] + [f'  {ln}' for ln in lines]))

    def _update_active(self):
        """Render whichever tab is currently visible. Returns the number of plotted trials."""
        self._update_recent_label()
        # Stats tab only ever changes on an explicit "Run stats" press — the poll timer must
        # not trigger the (expensive) permutation pipeline, so do nothing here for it.
        if self.tabs.currentWidget() is self.stats_tab:
            return 0
        # Upcoming-trials tab reads queued tasks straight from the experiment DB; it doesn't
        # use the compiled/completed-trial data or the behavioral filters.
        if self.tabs.currentWidget() is self.upcoming_tab:
            return self._render_upcoming()
        # Bias tab reads its own (estim-off variant/delta) view from the repository via
        # bias_analysis; it doesn't use the experiment-format frame or the behavioral filters.
        if self.tabs.currentWidget() is self.bias_scroll:
            return self._render_bias()
        window_tab = self.tabs.currentWidget() is self.win_scroll
        split_tab = self.tabs.currentWidget() is self.split_tab
        data_exp = self._read_and_filter(include_behavioral=window_tab)
        if data_exp is None:
            return 0
        if window_tab:
            self._render_window(data_exp)
        elif split_tab:
            self._render_split(data_exp)
        else:
            self._render_overview(data_exp)
        return len(data_exp)

    # ---- upcoming-trials tab -------------------------------------------
    def _selected_group_dims(self):
        """Return the checked grouping columns, in GROUP_DIMENSIONS order."""
        return [col for col, _label in GROUP_DIMENSIONS
                if self.upcoming_checks.get(col) is not None
                and self.upcoming_checks[col].isChecked()]

    @staticmethod
    def _fmt_upcoming_value(col, value):
        """Human-format a grouping value for the table (None -> em dash, noise -> %, bool ->
        yes/no)."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return '—'
        if col == 'noise_chance':
            return f'{float(value) * 100:.0f}%'
        if isinstance(value, (bool, np.bool_)):
            return 'yes' if value else 'no'
        if col in ('estim_spec_id', 'gen_id'):
            try:
                return str(int(value))
            except (TypeError, ValueError):
                return str(value)
        return str(value)

    def _render_upcoming(self):
        """Fill the upcoming-trials table with per-group counts of queued-but-unrun trials.
        Returns the total number of upcoming trials."""
        df = read_upcoming_trials(self.exp_conn)
        total = len(df)
        group_dims = self._selected_group_dims()
        counts = group_upcoming_counts(df, group_dims)
        # Stash the raw trials + grouping so a delete can map a selected row back to task_ids.
        self._upcoming_df = df
        self._upcoming_group_dims = group_dims

        table = self.upcoming_table
        table.setSortingEnabled(False)
        headers = [label for col, label in GROUP_DIMENSIONS if col in group_dims] + ['Count']
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(counts))
        for r in range(len(counts)):
            row = counts.iloc[r]
            # The group key (raw values) reconstructs this row's filter; stash it on the first
            # cell so the delete action survives the user re-sorting the table.
            group_key = {col: row[col] for col in group_dims}
            for c, col in enumerate(group_dims):
                item = QtWidgets.QTableWidgetItem(self._fmt_upcoming_value(col, row[col]))
                if c == 0:
                    item.setData(_USER_ROLE, group_key)
                table.setItem(r, c, item)
            count_item = QtWidgets.QTableWidgetItem()
            count_item.setData(_EDIT_ROLE, int(row['count']))
            if not group_dims:
                count_item.setData(_USER_ROLE, group_key)  # total-only row: empty key = all
            table.setItem(r, len(group_dims), count_item)
        table.setSortingEnabled(True)
        table.resizeColumnsToContents()

        self.upcoming_total_label.setText(f'{total} upcoming trials')
        self.status_label.setText(f'{self.session_id}: {total} upcoming trials')
        return total

    def _group_key_label(self, group_key, n):
        """Human description of a group (its dim=value pairs) and its trial count, for the
        delete confirmation dialog."""
        if not group_key:
            return f'ALL upcoming trials ({n})'
        labels = dict(GROUP_DIMENSIONS)
        parts = [f'{labels.get(col, col)}={self._fmt_upcoming_value(col, val)}'
                 for col, val in group_key.items()]
        return f'{", ".join(parts)}  ({n})'

    def _delete_selected_upcoming(self):
        """Delete the queued trials in the selected table row(s) from TaskToDo, after a
        confirmation showing the exact count. Each row corresponds to one condition group."""
        df = self._upcoming_df
        if df is None or len(df) == 0:
            return
        table = self.upcoming_table
        selected_rows = sorted({idx.row() for idx in table.selectionModel().selectedRows()})
        if not selected_rows:
            QtWidgets.QMessageBox.information(
                self, 'Delete upcoming trials', 'Select one or more group rows first.')
            return

        task_ids, descriptions = [], []
        for r in selected_rows:
            first_item = table.item(r, 0)
            if first_item is None:
                continue
            group_key = first_item.data(_USER_ROLE)
            if group_key is None:
                continue
            ids = task_ids_for_group(df, group_key)
            task_ids.extend(ids)
            descriptions.append(self._group_key_label(group_key, len(ids)))
        task_ids = sorted(set(task_ids))
        if not task_ids:
            return

        msg = ('Delete these upcoming trials from TaskToDo?\n\n  '
               + '\n  '.join(descriptions)
               + f'\n\nTotal: {len(task_ids)} trial(s). This cannot be undone.')
        if QtWidgets.QMessageBox.question(self, 'Delete upcoming trials', msg) != _MSG_YES:
            return
        try:
            deleted = delete_upcoming_tasks(self.exp_conn, task_ids)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Delete failed', str(e))
            return
        self.status_label.setText(f'{self.session_id}: deleted {deleted} upcoming trial(s)')
        self._render_upcoming()

    # ---- stats tab ------------------------------------------------------
    @staticmethod
    def _fmt_pval(p):
        if p < 0.001:
            return 'p<0.001'
        if p < 0.01:
            return f'p={p:.3f}'
        return f'p={p:.2f}'

    def _run_stats(self):
        """Run the by-condition + permutation pipeline for this session (persisting to the
        repository) and render the single-session max-stat and exceedance tests. Blocking."""
        metric = self.stats_metric_combo.currentData()
        studentize = self.stats_studentize_cb.isChecked()
        min_trials = self.stats_min_trials_spin.value()
        n_perm = self.stats_nperm_spin.value()

        app = QtWidgets.QApplication.instance()

        def progress(msg):
            self.stats_status_label.setText(msg)
            if app is not None:
                app.processEvents()

        self.stats_run_button.setEnabled(False)
        try:
            result = run_session_stats(
                self.session_id, self.session_date, metric,
                n_permutations=n_perm, min_trials=min_trials, studentize=studentize,
                progress=progress)
        except Exception as e:
            self.stats_status_label.setText(f'Stats failed: {e}')
            QtWidgets.QMessageBox.critical(self, 'Stats failed', str(e))
            return
        finally:
            self.stats_run_button.setEnabled(True)

        self._stats_result = result
        self._render_stats(result)
        self.stats_status_label.setText(
            f"Done — saved to repository (algorithm='{result['algorithm_label']}', "
            f"metric={metric}).")

    def _render_stats(self, result):
        self._render_maxstat_plot(result)
        self._render_exceedance_plot(result)

    def _render_maxstat_plot(self, result):
        """Bar chart: observed best (max-stat) effect vs the permutation null's mean, with the
        null 95th percentile as a line and the p-value in the title."""
        plot = self.stats_maxstat_plot
        plot.clear()
        unit = result['unit']
        ms = result['max_stat']
        if ms is None:
            plot.setTitle(f"Max-stat: no condition with ≥{result['min_trials']} trials/group")
            return

        xs = [0, 1]
        heights = [ms['observed'], ms['null_mean']]
        bar = pg.BarGraphItem(x=xs, height=heights, width=0.6,
                              brushes=[(214, 39, 40), (140, 140, 140)])
        plot.addItem(bar)
        # Null 95th percentile as a horizontal reference line.
        line = pg.InfiniteLine(pos=ms['null_95'], angle=0,
                               pen=pg.mkPen((80, 80, 80), style=_DASH_LINE))
        plot.addItem(line)
        p95_text = pg.TextItem(f"null 95th = {ms['null_95']:+.2f}{unit}", color=(80, 80, 80),
                               anchor=(0, 1))
        p95_text.setPos(-0.4, ms['null_95'])
        plot.addItem(p95_text)

        plot.getAxis('bottom').setTicks([[(0, f"Observed max\n({ms['observed']:+.2f}{unit})"),
                                          (1, f"Null mean\n({ms['null_mean']:+.2f}{unit})")]])
        plot.setLabel('left', f'Effect ({unit})')
        sig = ms['p_value'] < 0.05
        plot.setTitle(f"Max-stat test — {self._fmt_pval(ms['p_value'])}"
                      + ('  *' if sig else ''))
        plot.getViewBox().enableAutoRange()

    def _render_exceedance_plot(self, result):
        """This-session exceedance-count test: observed #conditions over each threshold vs the
        permutation null (mean + 95th percentile band), p-value annotated per threshold."""
        plot = self.stats_exceed_plot
        plot.clear()
        exc = result['exceedance']
        if exc is None or not exc.get('results'):
            plot.setTitle(f"Exceedance: no condition with ≥{result['min_trials']} trials/group")
            return

        res = exc['results']
        thr = [r['threshold'] for r in res]
        n_obs = [r['n_obs'] for r in res]
        null_mean = [r['null_mean'] for r in res]
        null_95 = [r['null_95'] for r in res]
        unit = exc.get('unit', '%')

        # Null 95th-percentile band (0..null_95) shaded, null mean dashed, observed solid red.
        zero_curve = plot.plot(thr, [0] * len(thr), pen=None)
        p95_curve = plot.plot(thr, null_95, pen=pg.mkPen((150, 150, 150)))
        plot.addItem(pg.FillBetweenItem(zero_curve, p95_curve, brush=(200, 200, 200, 90)))
        plot.plot(thr, null_mean, pen=pg.mkPen((120, 120, 120), style=_DASH_LINE),
                  symbol='o', symbolSize=5, symbolBrush=(120, 120, 120), name='Null mean')
        plot.plot(thr, n_obs, pen=pg.mkPen((214, 39, 40), width=2),
                  symbol='o', symbolSize=6, symbolBrush=(214, 39, 40), name='Observed')

        for r in res:
            sig = r['p_value'] < 0.05
            t = pg.TextItem(self._fmt_pval(r['p_value']),
                            color=(139, 0, 0) if sig else (120, 120, 120), anchor=(0.5, 1.0))
            t.setPos(r['threshold'], r['n_obs'])
            plot.addItem(t)

        plot.setLabel('bottom', f'Effect threshold ({unit})')
        plot.setLabel('left', '# conditions ≥ threshold')
        plot.setTitle(f"Exceedance-count test — {exc['n_conditions']} conditions, "
                      f"{exc['n_perms']} perms")
        plot.getViewBox().enableAutoRange()

    def _render_overview(self, data_exp):
        # Split-texture trials have their own tab (Texture Split); keep them out of the
        # Overview so they don't get bucketed into the delta/variant % curves and counts.
        data_exp = data_exp[data_exp['IsTextureSplit'] == False]
        partition = partition_estim_data(data_exp)
        rows = _rows_for(partition.include_removed)
        # Skip a column entirely when it has no data (e.g. its trial type was filtered out).
        cols = [c for c in _columns_for(partition) if (len(c[2]) + len(c[3])) > 0]
        if not cols:
            return
        self._ensure_grid(rows, cols)
        for r, (_row_title, kind) in enumerate(rows):
            for (col_key, _col_title, on_df, off_df, spec_ids) in cols:
                self._update_cell(r, col_key, kind, on_df, off_df, spec_ids)

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

        for r, (row_title, _kind) in enumerate(rows):
            for c, (col_key, col_title, *_rest) in enumerate(cols):
                # Background comes from the global setConfigOptions; do NOT pass background= to
                # GraphicsLayoutWidget (it forwards kwargs to GraphicsLayout, which rejects it).
                glw = _ScrollGraphicsLayout(self.scroll)
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

        # Only record the config once the grid is fully built, so a failure mid-build retries
        # next time instead of leaving an empty grid that matches the config (KeyError storms).
        self._grid_config = config

    def _color_for_spec(self, spec):
        """Return this spec's stable color, assigning the next palette entry on first sight."""
        spec = int(spec)
        if spec not in self._spec_color:
            self._spec_color[spec] = _SPEC_COLORS[len(self._spec_color) % len(_SPEC_COLORS)]
        return self._spec_color[spec]

    def _style_for_noise(self, noise):
        """Return this noise level's stable pen style, assigned on first sight."""
        noise = round(float(noise), 6)
        if noise not in self._noise_style:
            self._noise_style[noise] = _NOISE_STYLES[len(self._noise_style) % len(_NOISE_STYLES)]
        return self._noise_style[noise]

    def _style_for_combo(self, combo):
        """Return this behavioral-combo's stable pen style, assigned on first sight. Cycles the
        small style palette; color (spec / trial type) plus the legend label disambiguate fully
        when more combos exist than styles."""
        if combo not in self._combo_style:
            self._combo_style[combo] = _NOISE_STYLES[len(self._combo_style) % len(_NOISE_STYLES)]
        return self._combo_style[combo]

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

    # ---- texture-split tab ---------------------------------------------
    def _split_rows(self, df, combine_sample, combine_inverted):
        """Build (row_key, row_title, mask) for each active split/inverted combo present in df.

        A 'combined' dimension is pooled (None) rather than split into its own rows. Rows with no
        trials are dropped so the grid only shows conditions that actually have data."""
        sample_opts = [None] if combine_sample else [True, False]
        inverted_opts = [None] if combine_inverted else [True, False]
        rows = []
        for s in sample_opts:
            for inv in inverted_opts:
                def mask(d, s=s, inv=inv):
                    m = pd.Series(True, index=d.index)
                    if s is not None:
                        m &= (d['SplitRenderIsSample'] == s)
                    if inv is not None:
                        m &= (d['InvertedShading'] == inv)
                    return m
                if not mask(df).any():
                    continue
                sample_lbl = 'sample+foil' if s is None else ('split=sample' if s else 'split=distractor')
                inv_lbl = 'normal+inverted' if inv is None else ('inverted' if inv else 'normal')
                rows.append((f's={s}|i={inv}', f'{sample_lbl}, {inv_lbl}', mask))
        return rows

    def _render_split(self, data_exp):
        """% 3D grid for split-texture trials: rows = split/inverted combos (pooled per the
        combine toggles), columns = Variant/Delta. Each cell: % chose the 3D-limb option among
        match-vs-foil picks, vs noise, with the estim-off baseline + one curve per spec."""
        df = data_exp[data_exp['IsTextureSplit'] == True]
        if len(df) == 0:
            self.status_label.setText(f'{self.session_id}: no texture-split trials')
            return
        rows = self._split_rows(df, self.combine_sample_cb.isChecked(),
                                self.combine_inverted_cb.isChecked())
        cols = [('variant', 'Variant', False), ('delta', 'Delta', True)]
        cols = [c for c in cols if (df['IsDelta'] == c[2]).any()]
        if not rows or not cols:
            self.status_label.setText(f'{self.session_id}: no texture-split trials to plot')
            return
        self._ensure_split_grid(rows, cols)
        for (row_key, _row_title, mask) in rows:
            sub = df[mask(df)]
            for (col_key, _col_title, is_delta) in cols:
                coldf = sub[sub['IsDelta'] == is_delta]
                on_df = coldf[coldf['EStimEnabled'] == True]
                off_df = coldf[coldf['EStimEnabled'] == False]
                spec_ids = on_df['EStimSpecId'].dropna().unique()
                self._update_split_cell(row_key, col_key, on_df, off_df, spec_ids)

    def _ensure_split_grid(self, rows, cols):
        """(Re)build the split grid only when the row/column layout changes (combine toggles or a
        new condition appearing)."""
        config = (tuple(r[0] for r in rows), tuple(c[0] for c in cols))
        if config == self._split_grid_config:
            return
        while self.split_grid_layout.count():
            item = self.split_grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.split_plots, self.split_legends, self.split_series = {}, {}, {}
        for r, (row_key, row_title, *_rest) in enumerate(rows):
            for c, (col_key, col_title, *_crest) in enumerate(cols):
                glw = _ScrollGraphicsLayout(self.split_scroll)
                glw.setFixedHeight(PLOT_HEIGHT)
                pi = glw.addPlot(row=0, col=0)
                legend = pg.LegendItem(offset=(10, 10))
                glw.addItem(legend, row=0, col=1)
                glw.ci.layout.setColumnStretchFactor(0, 1)
                glw.ci.layout.setColumnFixedWidth(1, LEGEND_WIDTH)
                pi.setTitle(f'% 3D — {col_title}: {row_title}')
                pi.showGrid(x=True, y=True, alpha=0.3)
                pi.setLabel('left', '% chose 3D limb')
                pi.setLabel('bottom', 'Noise Chance (%)')
                vb = pi.getViewBox()
                vb.invertX(True)
                vb.setRange(xRange=(-5, 105), yRange=(0, 100), padding=0)
                vb.setLimits(yMin=0, yMax=100)
                vb.disableAutoRange()
                self.split_grid_layout.addWidget(glw, r, c)
                self.split_plots[(row_key, col_key)] = pi
                self.split_legends[(row_key, col_key)] = legend
        self._split_grid_config = config

    def _update_split_cell(self, row_key, col_key, on_df, off_df, spec_ids):
        plot = self.split_plots[(row_key, col_key)]
        legend = self.split_legends[(row_key, col_key)]
        wanted = {'OFF': (off_df, 'EStim OFF', pg.mkPen('k', width=2, style=_DASH_LINE), (0, 0, 0))}
        for spec in sorted(spec_ids):
            color = self._color_for_spec(spec)
            wanted[('spec', spec)] = (on_df[on_df['EStimSpecId'] == spec],
                                      f'Spec {int(spec)}', pg.mkPen(color, width=2), color)
        for series_key, (df, base, pen, color) in wanted.items():
            xs, ys, ns = curve_points(df, 'pct_3d')
            sid = (row_key, col_key, series_key)
            if sid not in self.split_series:
                curve = plot.plot([], [], pen=pen, symbol='o', symbolSize=6,
                                  symbolBrush=color, symbolPen=color)
                legend.addItem(curve, base)
                label = legend.items[-1][1] if legend.items else None
                self.split_series[sid] = {'curve': curve, 'label': label, 'base': base}
            entry = self.split_series[sid]
            entry['curve'].setData(xs, ys)
            if entry['label'] is not None:
                entry['label'].setText(f"{entry['base']} (n={int(sum(ns))})")
            self._sync_point_labels(plot, entry, xs, ys, ns, color)
        for sid in [s for s in self.split_series
                    if s[0] == row_key and s[1] == col_key and s[2] not in wanted]:
            entry = self.split_series.pop(sid)
            plot.removeItem(entry['curve'])
            for t in entry.get('texts', []):
                plot.removeItem(t)
            try:
                legend.removeItem(entry['curve'])
            except Exception:
                pass

    # ---- sliding-window tab --------------------------------------------
    def _render_window(self, data_exp):
        """Sliding-window panels: row 0 = effect-size per trial type (line = (spec, noise),
        color = spec shared with the overview, alpha = noise); row 1 = a full-width no-estim
        % correct baseline split by trial type (incl. behavioral) + Combined."""
        cond_cols = _window_cond_cols(data_exp)
        series_by_type = sliding_window_series(data_exp, cond_cols=cond_cols)
        baseline = sliding_window_baseline(data_exp, cond_cols=cond_cols)
        effect_types = [tt for tt in _TRIAL_TYPE_ORDER if tt in series_by_type]
        if not effect_types and not baseline:
            self.status_label.setText(f'{self.session_id}: not enough trials for a window')
            return
        self._ensure_window_grid(effect_types)
        for tt in effect_types:
            self._update_window_cell(tt, series_by_type[tt], cond_cols)
        self._update_baseline_cell(baseline, cond_cols)
        # Re-fit the X axis on every refresh so newly-appended windows are always visible
        # ("view all" along x). Y stays clamped to its fixed, comparable scale.
        for pi in self.win_plots.values():
            pi.getViewBox().enableAutoRange(x=True)

    def _make_window_panel(self, title, ylabel, yrange, zero_line):
        """Create a scrollable plot+legend panel for the sliding-window tab. Returns
        (widget, plot_item, legend)."""
        glw = _ScrollGraphicsLayout(self.win_scroll)
        glw.setMinimumHeight(WINDOW_PLOT_HEIGHT)
        pi = glw.addPlot(row=0, col=0)
        legend = pg.LegendItem(offset=(10, 10))
        glw.addItem(legend, row=0, col=1)
        glw.ci.layout.setColumnStretchFactor(0, 1)
        glw.ci.layout.setColumnFixedWidth(1, LEGEND_WIDTH)
        pi.setTitle(title)
        pi.showGrid(x=True, y=True, alpha=0.3)
        pi.setLabel('left', ylabel)
        pi.setLabel('bottom', 'Trial (window center)')
        if zero_line:
            pi.addLine(y=0, pen=pg.mkPen((120, 120, 120), style=_DASH_LINE))
        vb = pi.getViewBox()
        # y is clamped to its meaningful range; x auto-fits the trials as they accumulate so
        # the newest window is always in view (re-asserted each refresh in _render_window).
        vb.setYRange(yrange[0], yrange[1], padding=0)
        vb.setLimits(yMin=yrange[0], yMax=yrange[1])
        vb.enableAutoRange(x=True)
        return glw, pi, legend

    def _ensure_window_grid(self, effect_types):
        """(Re)build the sliding-window grid only when the set of effect-size trial types
        changes. Row 0: one effect-size panel per trial type; row 1: a full-width baseline."""
        config = tuple(effect_types)
        if config == self._win_config:
            return

        while self.win_grid_layout.count():
            item = self.win_grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.win_plots, self.win_legends, self.win_series = {}, {}, {}

        n_cols = max(len(effect_types), 1)
        for c, tt in enumerate(effect_types):
            glw, pi, legend = self._make_window_panel(
                tt, 'Effect size (ON − OFF, % hyp vs delta)', (-100, 100), zero_line=True)
            self.win_grid_layout.addWidget(glw, 0, c)
            self.win_plots[tt] = pi
            self.win_legends[tt] = legend

        # Full-width no-estim % correct baseline, spanning all effect columns.
        glw, pi, legend = self._make_window_panel(
            'No-estim % correct (by trial type)', '% correct', (0, 100), zero_line=False)
        self.win_grid_layout.addWidget(glw, 1, 0, 1, n_cols)
        self.win_plots['__baseline__'] = pi
        self.win_legends['__baseline__'] = legend

        self._win_config = config

    def _update_window_cell(self, trial_type, series, cond_cols):
        plot = self.win_plots[trial_type]
        legend = self.win_legends[trial_type]

        wanted = set()
        for (spec, combo), (xs, ys) in sorted(series.items(),
                                              key=lambda kv: (kv[0][0], _combo_sort_key(kv[0][1]))):
            wanted.add((spec, combo))
            base = self._color_for_spec(spec)
            # Color = spec; line style = behavioral combo (primary); alpha = noise (secondary cue).
            noise = _combo_value(cond_cols, combo, 'NoiseChance')
            alpha = int(_alpha_for_noise(noise) * 255) if noise is not None else 255
            color = (base[0], base[1], base[2], alpha)
            pen = pg.mkPen(color, width=2, style=self._style_for_combo(combo))
            sid = (trial_type, spec, combo)
            if sid not in self.win_series:
                curve = plot.plot([], [], pen=pen)
                legend.addItem(curve, f'Spec {spec} | {_format_window_combo(cond_cols, combo)}')
                self.win_series[sid] = {'curve': curve}
            self.win_series[sid]['curve'].setData(xs, ys)

        # Drop (spec, combo) lines no longer present.
        for sid in [s for s in self.win_series if s[0] == trial_type and (s[1], s[2]) not in wanted]:
            entry = self.win_series.pop(sid)
            plot.removeItem(entry['curve'])
            try:
                legend.removeItem(entry['curve'])
            except Exception:
                pass

    def _update_baseline_cell(self, baseline, cond_cols):
        """Update the no-estim % correct baseline: one line per (trial type, behavioral combo),
        incl. behavioral trials, plus a dashed pooled Combined line. Color = trial type (shared
        with the rest of the baseline), line style = behavioral combo (shared with the
        effect-size panels)."""
        plot = self.win_plots['__baseline__']
        legend = self.win_legends['__baseline__']

        type_order = list(_ALL_TRIAL_TYPES) + ['Combined']

        def sort_key(item):
            (tt, combo) = item[0]
            idx = type_order.index(tt) if tt in type_order else len(type_order)
            return (idx, _combo_sort_key(combo))

        wanted = set()
        for (tt, combo), (xs, ys) in sorted(baseline.items(), key=sort_key):
            wanted.add((tt, combo))
            color = _BASELINE_COLORS.get(tt, (127, 127, 127))
            is_combined = (tt == 'Combined')
            sid = ('__baseline__', tt, combo)
            if sid not in self.win_series:
                style = _DASH_LINE if is_combined else self._style_for_combo(combo)
                pen = pg.mkPen(color, width=2, style=style) if style else pg.mkPen(color, width=2)
                curve = plot.plot([], [], pen=pen)
                label = tt if (is_combined or not combo) \
                    else f'{tt} | {_format_window_combo(cond_cols, combo)}'
                legend.addItem(curve, label)
                self.win_series[sid] = {'curve': curve}
            self.win_series[sid]['curve'].setData(xs, ys)

        for sid in [s for s in self.win_series if s[0] == '__baseline__' and (s[1], s[2]) not in wanted]:
            entry = self.win_series.pop(sid)
            plot.removeItem(entry['curve'])
            try:
                legend.removeItem(entry['curve'])
            except Exception:
                pass

    # ---- bias tab -------------------------------------------------------
    # The top-bar filters were built against the experiment-format column names; the bias frame
    # uses the repository column names. This maps one filter widget to its bias column.
    _BIAS_FILTER_COLUMNS = (
        ('noise_filter',    'noise_chance'),
        ('type_filter',     'trial_type'),
        ('sl_filter',       'sample_length'),
        ('nchoices_filter', 'num_choices'),
        ('nproc_filter',    'num_procedural_distractors'),
        ('nrand_filter',    'num_rand_distractors'),
    )

    def _sync_bias_filters(self, trials):
        """Populate the shared top-bar filters with the values present in the bias data (sync only
        adds, never removes, so this never fights the other tabs' syncing)."""
        if trials is None or len(trials) == 0:
            return
        self.noise_filter.sync(sorted(trials['noise_chance'].dropna().unique()))
        self.type_filter.sync([t for t in _ALL_TRIAL_TYPES if (trials['trial_type'] == t).any()])
        self.sl_filter.sync(sorted(trials['sample_length'].dropna().unique(), key=float))
        self.nchoices_filter.sync(sorted(trials['num_choices'].dropna().unique(), key=float))
        self.nproc_filter.sync(sorted(trials['num_procedural_distractors'].dropna().unique(), key=float))
        self.nrand_filter.sync(sorted(trials['num_rand_distractors'].dropna().unique(), key=float))

    def _apply_bias_filters(self, trials):
        """Drop bias trials excluded by the top-bar behavioral-parameter filters."""
        df = trials
        for attr, column in self._BIAS_FILTER_COLUMNS:
            sel = getattr(self, attr).selected()
            if sel is not None and column in df.columns:
                df = df[df[column].isin(sel)]
        return df

    def _render_bias(self):
        """Render the Bias tab: one row per lineage group (variant + its deltas), showing the
        per-sample pick distribution (bars, coloured by which member was picked) and its
        sliding-window version. Reads estim-off variant/delta trials from the repository through
        bias_analysis, honouring the start/max-gen filters. Returns the trial count."""
        try:
            trials = bias.read_bias_trials(
                self.session_id, start_gen_id=self.start_gen_id, max_gen_id=self.max_gen_id)
        except Exception as e:
            self.status_label.setText(f'Bias error: {e}')
            return 0

        # Offer the top-bar behavioral-parameter filters the values present in the bias data, then
        # apply the current selection — so the same Noise / Trial type / Sample len / #Choices /
        # #Proc / #Rand filters that drive the other tabs also subset the bias view.
        self._sync_bias_filters(trials)
        trials = self._apply_bias_filters(trials)

        try:
            # Thumbnails are resolved lazily when the grid is (re)built (see
            # _make_bias_thumbnail_panel), not on every refresh, so skip them here.
            result = bias.compute_session_bias(
                self.session_id, trials_df=trials,
                window=WINDOW_SIZE, step=WINDOW_STEP, with_thumbnails=False)
        except Exception as e:
            self.status_label.setText(f'Bias error: {e}')
            return 0

        groups = result['groups']
        n_trials = len(trials)
        if not groups:
            self._ensure_bias_grid([])
            self.status_label.setText(
                f'{self.session_id}: no behavioural (estim-off) variant/delta trials '
                f'match the current filters')
            return 0

        self._ensure_bias_grid(groups)
        for group in groups:
            self._update_bias_bars(group)
            self._update_bias_timeseries(group)
        self.status_label.setText(f'{self.session_id}: bias over {n_trials} behavioural trials')
        return n_trials

    @staticmethod
    def _rgb_css(color):
        return f'rgb({color[0]}, {color[1]}, {color[2]})'

    def _make_bias_thumbnail_panel(self, group):
        """Column 0 for a group: each member's thumbnail (or a colour swatch fallback) with a
        border in the member's assigned colour — this doubles as the legend for the two plots."""
        panel = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(panel)
        vbox.setContentsMargins(2, 2, 2, 2)
        vbox.setSpacing(2)
        vbox.addWidget(QtWidgets.QLabel(f"Group {group['variant_id']}"))

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        members = group['member_ids']
        for i, member in enumerate(members):
            color = group['colors'][int(member)]
            role = 'variant' if i == 0 else 'delta'

            cell = QtWidgets.QVBoxLayout()
            cell.setSpacing(1)
            img = QtWidgets.QLabel()
            img.setAlignment(_ALIGN_CENTER)
            img.setFixedSize(BIAS_THUMB_PX, BIAS_THUMB_PX)
            try:
                path = bias.resolve_thumbnail(int(member))
            except Exception:
                path = None
            pixmap = QtGui.QPixmap(path) if path else QtGui.QPixmap()
            if not pixmap.isNull():
                img.setPixmap(pixmap.scaled(BIAS_THUMB_PX - 8, BIAS_THUMB_PX - 8,
                                            _KEEP_ASPECT, _SMOOTH_TRANSFORM))
                img.setStyleSheet(f'border: 3px solid {self._rgb_css(color)};')
            else:
                # No thumbnail on disk — show a solid colour swatch so the legend colour is clear.
                img.setStyleSheet(
                    f'border: 3px solid {self._rgb_css(color)}; '
                    f'background-color: {self._rgb_css(color)};')
            cell.addWidget(img)
            cap = QtWidgets.QLabel(f'{role}\n{int(member)}')
            cap.setAlignment(_ALIGN_CENTER)
            cap.setStyleSheet('font-size: 9px; color: #444;')
            cell.addWidget(cap)
            row.addLayout(cell)
        row.addStretch(1)
        vbox.addLayout(row)
        vbox.addStretch(1)
        return panel

    def _ensure_bias_grid(self, groups):
        """(Re)build the bias grid only when the set/shape of groups changes. Columns: thumbnails
        (legend), per-sample pick bars, sliding-window time series."""
        config = tuple((g['variant_id'], tuple(g['member_ids'])) for g in groups)
        if config == self._bias_config:
            return

        while self.bias_grid_layout.count():
            item = self.bias_grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.bias_bar_plots, self.bias_ts_plots, self.bias_ts_legends = {}, {}, {}
        self.bias_bar_items, self.bias_ts_series = {}, {}

        self.bias_grid_layout.setColumnStretch(0, 0)
        self.bias_grid_layout.setColumnStretch(1, 3)
        self.bias_grid_layout.setColumnStretch(2, 3)

        for r, group in enumerate(groups):
            vid = group['variant_id']

            self.bias_grid_layout.addWidget(self._make_bias_thumbnail_panel(group), r, 0)

            # Bars: % picked, per sample. No legend column (thumbnails are the legend).
            glw_bar = _ScrollGraphicsLayout(self.bias_scroll)
            glw_bar.setFixedHeight(BIAS_ROW_HEIGHT)
            pi_bar = glw_bar.addPlot(row=0, col=0)
            pi_bar.setTitle(f'Group {vid}: % picked, by sample')
            pi_bar.showGrid(x=False, y=True, alpha=0.3)
            pi_bar.setLabel('left', '% picked')
            vb = pi_bar.getViewBox()
            vb.setYRange(0, 100, padding=0)
            vb.setLimits(yMin=0, yMax=100)
            self.bias_grid_layout.addWidget(glw_bar, r, 1)
            self.bias_bar_plots[vid] = pi_bar

            # Time series: one line per (sample, picked), colour=picked, style=sample.
            glw_ts = _ScrollGraphicsLayout(self.bias_scroll)
            glw_ts.setFixedHeight(BIAS_ROW_HEIGHT)
            pi_ts = glw_ts.addPlot(row=0, col=0)
            legend = pg.LegendItem(offset=(10, 10))
            glw_ts.addItem(legend, row=0, col=1)
            glw_ts.ci.layout.setColumnStretchFactor(0, 1)
            glw_ts.ci.layout.setColumnFixedWidth(1, LEGEND_WIDTH)
            pi_ts.setTitle(f'Group {vid}: % picked over trials')
            pi_ts.showGrid(x=True, y=True, alpha=0.3)
            pi_ts.setLabel('left', '% picked')
            pi_ts.setLabel('bottom', 'Trial (window center)')
            vb = pi_ts.getViewBox()
            vb.setYRange(0, 100, padding=0)
            vb.setLimits(yMin=0, yMax=100)
            vb.enableAutoRange(x=True)
            self.bias_grid_layout.addWidget(glw_ts, r, 2)
            self.bias_ts_plots[vid] = pi_ts
            self.bias_ts_legends[vid] = legend

        self._bias_config = config

    def _update_bias_bars(self, group):
        """Draw/redraw one group's bar chart: clusters along x are samples; within a cluster, one
        bar per member, coloured by the picked member; height = % of that sample's trials picked."""
        vid = group['variant_id']
        plot = self.bias_bar_plots.get(vid)
        if plot is None:
            return
        old = self.bias_bar_items.pop(vid, None)
        if old is not None:
            plot.removeItem(old)

        members = [int(m) for m in group['member_ids']]
        colors = group['colors']
        bars = group['bars']
        samples = [m for m in members if m in bars]   # keep member order
        m_count = len(members)

        xs, heights, brushes = [], [], []
        ticks = []
        for i, sample in enumerate(samples):
            base_x = i * (m_count + 1)
            for j, picked in enumerate(members):
                xs.append(base_x + j)
                heights.append(bars[sample]['pct'][picked])
                brushes.append(colors[picked])
            center = base_x + (m_count - 1) / 2.0
            ticks.append((center, f"smp {sample}\n(n={bars[sample]['n']})"))

        if not xs:
            return
        bar_item = pg.BarGraphItem(x=xs, height=heights, width=0.85, brushes=brushes)
        plot.addItem(bar_item)
        self.bias_bar_items[vid] = bar_item
        plot.getAxis('bottom').setTicks([ticks])
        plot.getViewBox().setXRange(-0.7, max(xs) + 0.7, padding=0)

    def _bias_sample_style(self, members, sample):
        """Stable pen style per sample (its index among the group's members)."""
        idx = members.index(int(sample)) if int(sample) in members else 0
        return _NOISE_STYLES[idx % len(_NOISE_STYLES)]

    def _update_bias_timeseries(self, group):
        """Draw/redraw one group's sliding-window time series. One line per (sample, picked):
        colour = picked member (matches the bars/thumbnails), line style = which sample."""
        vid = group['variant_id']
        plot = self.bias_ts_plots.get(vid)
        legend = self.bias_ts_legends.get(vid)
        if plot is None:
            return
        members = [int(m) for m in group['member_ids']]
        colors = group['colors']
        ts = group['timeseries']

        wanted = set()
        for (sample, picked), (xs, ys) in sorted(ts.items()):
            sample, picked = int(sample), int(picked)
            wanted.add((sample, picked))
            color = colors[picked]
            pen = pg.mkPen(color, width=2, style=self._bias_sample_style(members, sample))
            sid = (vid, sample, picked)
            if sid not in self.bias_ts_series:
                curve = plot.plot([], [], pen=pen)
                legend.addItem(curve, f'smp {sample} → {picked}')
                self.bias_ts_series[sid] = curve
            self.bias_ts_series[sid].setData(xs, ys)

        # Drop lines no longer present.
        for sid in [s for s in self.bias_ts_series if s[0] == vid and (s[1], s[2]) not in wanted]:
            curve = self.bias_ts_series.pop(sid)
            plot.removeItem(curve)
            try:
                legend.removeItem(curve)
            except Exception:
                pass


def main():
    ensure_estimshape_trials_table()
    exp_conn = Connection(context.nafc_database)
    session_id, session_date = read_session_id_and_date_from_db_name(context.nafc_database)

    app = QtWidgets.QApplication(sys.argv)
    window = LiveEstimWindow(exp_conn, session_id, session_date)
    window.show()
    # PyQt6/PySide6 use exec(); PyQt5 uses exec_().
    run = app.exec if hasattr(app, 'exec') else app.exec_
    sys.exit(run())


if __name__ == '__main__':
    main()

"""
Interactive GUI explorer for the estim-isolation-vs-effect analysis.

``analyze_estim_isolation_effect`` relates the estim effect on behaviour to a
family of tuning-geometry metrics (neighbour similarity / isolation) and a
current metric (``current_per_second``), per estim spec, across trial types. It
answers those questions by writing a wall of static figures — one per
(metric, aggregation, trial_type, ...) combination.

This module turns that same data into a single interactive window so you can
flip through the plots one at a time instead of regenerating figures:

  * X axis (``metric``)  — any neighbour-similarity metric, an isolation/PC
    column, or a current metric (``current_per_second`` / ``n_active_channels`` /
    ``total_current_uA``).
  * ``aggregation``      — mean vs worst (only meaningful for the neighbour
    metrics; ignored for the current/isolation columns).
  * ``trial_type``       — a single behavioural trial type, or all pooled.
  * ``split by``         — an optional per-spec condition (polarity, shape,
    num channels, a1, current bin, session, trial type). When set, the one plot
    fans out into a grid of subplots, one per value of that condition, each with
    its own trend line and correlation — so you can see whether the
    metric<->effect relationship holds within each condition.

Y is always the raw estim effect (ON - OFF %), or its magnitude when ``|effect|``
is ticked.

The expensive part — reading trial data per session to compute the per-spec
effect — is done ONCE at launch and cached. Changing the neighbourhood size
(``n_neighbors``) only re-joins the stored scores (cheap). Everything else is an
in-memory filter/redraw, so the controls respond instantly.

Run this file to launch the explorer (needs compute_estim_neighbor_scores to
have populated EStimNeighborScores first, same as the static analysis). Defaults
come from the shared ``COMPARISON_*`` config in analyze_estim_isolation_effect.
"""

import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection

from src.analysis.nafc.group_analysis import analyze_estim_isolation_effect as iso
from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
    _correlation,
    _effect_and_current_table,
    _fetch_isolation_scores,
    _fetch_neighbor_scores,
    _join_neighbor_scores,
    _discover_trial_types,
    _rc_for_trial_type,
    _isolation_axis_hint,
    _METRIC_LABELS,
    _METRIC_ORDER,
    COMPARISON_METRIC,
    COMPARISON_REQUIRED_CONDITIONS,
    COMPARISON_START_SESSION_ID,
    COMPARISON_EXCLUDE_SESSION_IDS,
    COMPARISON_MIN_ON_TRIALS,
    COMPARISON_MIN_OFF_TRIALS,
    COMPARISON_TRIAL_TYPES,
)

AGGREGATIONS = ('mean', 'worst')

# The current/dose columns that live directly on the effect table (no aggregation).
CURRENT_COLUMNS = {
    'current_per_second': 'current_per_second (µA·Hz)',
    'n_active_channels': 'n active channels',
    'total_current_uA': 'total current (µA)',
}

# Isolation / PC-neighbour columns (from EStimParameterData); no aggregation.
ISOLATION_COLUMN_LABELS = {
    'estim_min_isolation_um': 'min isolation (µm)',
    'estim_mean_isolation_um': 'mean isolation (µm)',
    'estim_mean_pc_neighbor_dist': 'mean PC-neighbour dist',
    'estim_max_pc_neighbor_dist': 'max PC-neighbour dist',
}

# Candidate condition columns to split subplots by: display label -> column name.
# Only those present with >1 distinct value are offered in the dropdown.
SPLIT_OPTIONS = [
    ('None (single plot)', None),
    ('polarity', 'polarity'),
    ('shape', 'shape'),
    ('num channels', 'n_active_channels'),
    ('a1 (µA)', 'a1_uA'),
    ('current bin', 'current_bin'),
    ('session', 'session_id'),
    ('trial type', 'trial_type'),
]

# When splitting by a numeric current metric, use these quantile-based bins.
_N_CURRENT_BINS = 4


# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------

def _fetch_estim_spec_attributes(session_ids=None):
    """Return {(session_id, estim_spec_id): {polarity, shape, a1_uA, total_current_uA}}
    from EStimParameters, reading per-spec estim attributes from the active
    (a1 > 0) channels. These are the categorical/parameter columns available to
    split subplots by. shape/polarity are uniform per spec under the current
    paradigm, so MIN() just picks that single value."""
    conn = Connection("allen_data_repository")
    base = ("SELECT session_id, estim_spec_id, MIN(polarity) AS polarity, "
            "MIN(shape) AS shape, MIN(a1) AS a1_uA, SUM(a1) AS total_current "
            "FROM EStimParameters WHERE a1 > 0")
    if session_ids:
        placeholders = ', '.join(['%s'] * len(session_ids))
        conn.execute(f"{base} AND session_id IN ({placeholders}) "
                     "GROUP BY session_id, estim_spec_id", tuple(session_ids))
    else:
        conn.execute(f"{base} GROUP BY session_id, estim_spec_id")

    out = {}
    for sess_id, spec_id, polarity, shape, a1_uA, total_current in conn.fetch_all():
        out[(sess_id, int(spec_id))] = {
            'polarity': polarity,
            'shape': shape,
            'a1_uA': float(a1_uA) if a1_uA is not None else None,
            'total_current_uA': float(total_current) if total_current is not None else None,
        }
    return out


class ExplorerData:
    """Holds the cached per-(session, spec, trial_type) table and re-joins the
    neighbour-metric scores on demand (per n_neighbors)."""

    def __init__(self, *, metric=COMPARISON_METRIC,
                 base_required_conditions=None,
                 start_session_id=COMPARISON_START_SESSION_ID,
                 exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
                 trial_types=None, exclude_other_estim=True):
        self.metric = metric
        self.base_required_conditions = base_required_conditions
        self.start_session_id = start_session_id
        self.exclude_session_ids = exclude_session_ids
        self.exclude_other_estim = exclude_other_estim

        if trial_types is None:
            trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
        self.trial_types = list(trial_types)

        self.df = pd.DataFrame()
        self.session_ids = []
        self.metric_names = []
        self.n_neighbors = None
        self._available_nb = []

    # -- expensive build (once) --------------------------------------------

    def build(self):
        """Build the effect + current + condition table once (reads trial data
        per session). Independent of neighbourhood size."""
        frames = []
        for tt in self.trial_types:
            rc = _rc_for_trial_type(self.base_required_conditions, tt)
            print(f"\n--- effect table for trial_type={tt!r} ---")
            df_tt = _effect_and_current_table(
                start_session_id=self.start_session_id,
                exclude_session_ids=self.exclude_session_ids,
                metric=self.metric, required_conditions=rc)
            if len(df_tt) == 0:
                print(f"  (no specs for trial_type={tt!r})")
                continue
            df_tt['trial_type'] = tt
            frames.append(df_tt)

        if not frames:
            self.df = pd.DataFrame()
            return self

        df = pd.concat(frames, ignore_index=True)
        self.session_ids = sorted(df['session_id'].unique().tolist())

        # Per-spec categorical/parameter attributes for splitting subplots.
        attrs = _fetch_estim_spec_attributes(self.session_ids)
        for col in ('polarity', 'shape', 'a1_uA', 'total_current_uA'):
            df[col] = [
                (attrs.get((s, int(spec)), {}) or {}).get(col)
                for s, spec in zip(df['session_id'], df['estim_spec_id'])]

        # Isolation / PC-neighbour columns (n_neighbors-independent).
        iso_scores = _fetch_isolation_scores(self.session_ids)
        for col in ISOLATION_COLUMN_LABELS:
            df[col] = [
                (iso_scores.get((s, int(spec)), {}) or {}).get(col)
                for s, spec in zip(df['session_id'], df['estim_spec_id'])]

        # Quantile bins of current for the "current bin" split option.
        df['current_bin'] = _quantile_bin_labels(df['current_per_second'],
                                                  _N_CURRENT_BINS)

        self.df = df
        self._available_nb = iso._available_n_neighbors(self.exclude_other_estim)
        return self

    @property
    def available_n_neighbors(self):
        return self._available_nb

    # -- cheap re-join per n_neighbors -------------------------------------

    def set_n_neighbors(self, n_neighbors):
        """(Re)join the neighbour-metric score columns for a given n_neighbors.
        Cheap: only a DB score fetch + column rebuild; the effect table is cached."""
        if len(self.df) == 0:
            return []
        # Drop any previously joined metric columns.
        old = [c for c in self.df.columns if c.endswith('__mean') or c.endswith('__worst')]
        if old:
            self.df.drop(columns=old, inplace=True)

        scores, metric_names = _fetch_neighbor_scores(
            self.session_ids, n_neighbors=int(n_neighbors),
            exclude_other_estim=self.exclude_other_estim)
        _join_neighbor_scores(self.df, scores, metric_names, aggregations=AGGREGATIONS)
        self.metric_names = metric_names
        self.n_neighbors = int(n_neighbors)
        return metric_names


def _quantile_bin_labels(series, n_bins):
    """Return a categorical Series binning `series` into up to `n_bins` quantile
    bins with readable 'lo–hi' labels, or all-NaN if there isn't enough spread."""
    values = pd.to_numeric(series, errors='coerce')
    finite = values.dropna()
    if finite.nunique() < 2:
        return pd.Series([np.nan] * len(series), index=series.index)
    try:
        edges = np.unique(np.nanquantile(finite.to_numpy(),
                                         np.linspace(0, 1, n_bins + 1)))
    except Exception:
        return pd.Series([np.nan] * len(series), index=series.index)
    if len(edges) < 2:
        return pd.Series([np.nan] * len(series), index=series.index)
    labels = [f"{edges[i]:g}–{edges[i + 1]:g}" for i in range(len(edges) - 1)]
    return pd.cut(values, bins=edges, labels=labels, include_lowest=True)


# ---------------------------------------------------------------------------
# X-axis metric options
# ---------------------------------------------------------------------------

class XOption:
    """One selectable X-axis quantity: display key, resolver to a column, and
    whether it uses the mean/worst aggregation."""

    def __init__(self, key, label, *, kind, base=None, higher_is_worse=False,
                 axis_hint=None):
        self.key = key
        self.label = label
        self.kind = kind              # 'metric' | 'current' | 'isolation'
        self.base = base or key
        self.higher_is_worse = higher_is_worse
        self.axis_hint = axis_hint

    @property
    def uses_aggregation(self):
        return self.kind == 'metric'

    def column(self, aggregation):
        if self.kind == 'metric':
            return f"{self.base}__{aggregation}"
        return self.base

    def axis_label(self, aggregation):
        if self.kind == 'metric':
            return f"{self.label}  ({aggregation})"
        if self.axis_hint:
            return f"{self.label}  ({self.axis_hint})"
        return self.label


def build_x_options(data):
    """Ordered list of XOption for the metric dropdown, given the loaded data:
    neighbour metrics first (known order), then current columns, then whichever
    isolation columns are actually populated."""
    options = []
    ordered = [m for m in _METRIC_ORDER if m in data.metric_names]
    ordered += sorted(m for m in data.metric_names if m not in _METRIC_ORDER)
    for name in ordered:
        options.append(XOption(name, _METRIC_LABELS.get(name, name), kind='metric',
                               base=name))
    for col, label in CURRENT_COLUMNS.items():
        if col in data.df.columns and data.df[col].notna().any():
            options.append(XOption(col, label, kind='current', base=col))
    for col, label in ISOLATION_COLUMN_LABELS.items():
        if col in data.df.columns and data.df[col].notna().any():
            options.append(XOption(col, label, kind='isolation', base=col,
                                   higher_is_worse=col in iso.HIGHER_IS_WORSE_COLUMNS,
                                   axis_hint=_isolation_axis_hint(col)))
    return options


def available_split_options(df):
    """SPLIT_OPTIONS restricted to columns present with >1 non-null distinct value
    (plus the always-present 'None')."""
    out = []
    for label, col in SPLIT_OPTIONS:
        if col is None:
            out.append((label, col))
            continue
        if col in df.columns and df[col].dropna().nunique() > 1:
            out.append((label, col))
    return out


# ---------------------------------------------------------------------------
# Plotting (backend-agnostic: draws onto a provided Figure)
# ---------------------------------------------------------------------------

def _panel_values(sorted_unique):
    """Human-friendly ordering of split values (numeric-aware)."""
    try:
        return sorted(sorted_unique)
    except Exception:
        return list(sorted_unique)


def _draw_panel(ax, sub, x_col, y_col, *, x_label, y_label, title,
                color_by_session, abs_effect, session_colors):
    """Scatter + least-squares trend + correlation annotation on one axes."""
    if len(sub) == 0:
        ax.set_title(f"{title}\n(no data)", fontsize=9)
        ax.axis('off')
        return

    if color_by_session and session_colors is not None:
        for s, sub_s in sub.groupby('session_id'):
            ax.scatter(sub_s[x_col], sub_s[y_col], s=45, alpha=0.8,
                       color=session_colors.get(s, '#888888'),
                       edgecolors='black', linewidths=0.4, label=str(s))
    else:
        ax.scatter(sub[x_col], sub[y_col], s=45, alpha=0.8, color='steelblue',
                   edgecolors='black', linewidths=0.4)

    xs = pd.to_numeric(sub[x_col], errors='coerce').to_numpy(dtype=float)
    ys = pd.to_numeric(sub[y_col], errors='coerce').to_numpy(dtype=float)
    good = np.isfinite(xs) & np.isfinite(ys)
    if good.sum() >= 2:
        slope, intercept = np.polyfit(xs[good], ys[good], 1)
        x_line = np.array([xs[good].min(), xs[good].max()])
        ax.plot(x_line, slope * x_line + intercept, color='red', linewidth=2,
                alpha=0.85)

    if not abs_effect:
        ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)

    corr = _correlation(xs[good], ys[good]) if good.sum() >= 3 else None
    full_title = title
    if corr:
        full_title += f"\nn={corr['n']}  r={corr['pearson_r']:.2f}"
        if corr['pearson_p'] is not None:
            full_title += f" (p={corr['pearson_p']:.2g})"
    else:
        full_title += f"\nn={int(good.sum())}"
    ax.set_title(full_title, fontsize=10)
    ax.set_xlabel(x_label, fontsize=9)
    ax.set_ylabel(y_label, fontsize=9)
    ax.grid(True, alpha=0.3)


def draw_explorer_plot(fig, df, x_option, *, aggregation, trial_type, split_col,
                       abs_effect=False, color_by_session=True,
                       min_on_trials=COMPARISON_MIN_ON_TRIALS,
                       min_off_trials=COMPARISON_MIN_OFF_TRIALS):
    """Render the current selection onto `fig` (cleared first).

    trial_type=None means pool all trial types. split_col=None means one plot;
    otherwise one subplot per distinct value of that column."""
    fig.clear()
    x_col = x_option.column(aggregation)
    y_label = '|effect| (|ON − OFF| %)' if abs_effect else 'effect (ON − OFF %)'
    x_label = x_option.axis_label(aggregation)

    if x_col not in df.columns:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, f"Column '{x_col}' not available.\n"
                          f"(Try a different n_neighbors or metric.)",
                ha='center', va='center', fontsize=11)
        ax.axis('off')
        return

    base = df
    if trial_type is not None and 'trial_type' in base.columns:
        base = base[base['trial_type'] == trial_type]
    base = base[
        base['effect_size'].notna()
        & base[x_col].notna()
        & (base['n_on'] >= min_on_trials)
        & (base['n_off'] >= min_off_trials)
    ].copy()
    base['_y'] = base['effect_size'].abs() if abs_effect else base['effect_size']

    session_colors = None
    if color_by_session:
        import matplotlib.pyplot as plt
        sessions = sorted(base['session_id'].unique())
        cmap = plt.get_cmap('tab20', max(len(sessions), 1))
        session_colors = {s: cmap(i) for i, s in enumerate(sessions)}

    tt_desc = trial_type if trial_type is not None else 'all trial types (pooled)'

    if split_col is None:
        ax = fig.add_subplot(111)
        _draw_panel(ax, base, x_col, '_y', x_label=x_label, y_label=y_label,
                    title=f"{x_option.label} — {tt_desc}",
                    color_by_session=color_by_session, abs_effect=abs_effect,
                    session_colors=session_colors)
        if color_by_session and session_colors is not None and len(session_colors) <= 20:
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                # de-dup while preserving order
                seen, h2, l2 = set(), [], []
                for h, l in zip(handles, labels):
                    if l not in seen:
                        seen.add(l)
                        h2.append(h)
                        l2.append(l)
                ax.legend(h2, l2, bbox_to_anchor=(1.02, 1), loc='upper left',
                          fontsize=7, title='session', framealpha=0.9)
        fig.suptitle(f"Estim {y_label.split(' ')[0]} vs {x_option.label}",
                     fontsize=12, fontweight='bold')
        return

    # Split into subplots, one per distinct split value.
    values = _panel_values(pd.unique(base[split_col].dropna()))
    if len(values) == 0:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, f"No data to split by '{split_col}'.",
                ha='center', va='center', fontsize=11)
        ax.axis('off')
        return

    n = len(values)
    ncols = min(3, n)
    nrows = int(np.ceil(n / ncols))
    axes = fig.subplots(nrows, ncols, squeeze=False)
    for i, val in enumerate(values):
        ax = axes[i // ncols][i % ncols]
        sub = base[base[split_col] == val]
        _draw_panel(ax, sub, x_col, '_y', x_label=x_label, y_label=y_label,
                    title=f"{split_col} = {val}",
                    color_by_session=color_by_session, abs_effect=abs_effect,
                    session_colors=session_colors)
    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    fig.suptitle(f"Estim {y_label.split(' ')[0]} vs {x_option.label} "
                 f"({aggregation if x_option.uses_aggregation else 'raw'}) — "
                 f"{tt_desc}, split by {split_col}",
                 fontsize=12, fontweight='bold')


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------

def launch_gui(data=None, **build_kwargs):
    """Build the data (if not supplied) and open the interactive explorer window.

    build_kwargs are forwarded to ExplorerData (metric, start_session_id,
    exclude_session_ids, base_required_conditions, trial_types, exclude_other_estim)."""
    import tkinter as tk
    from tkinter import ttk
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import (
        FigureCanvasTkAgg, NavigationToolbar2Tk)

    if data is None:
        print("Building explorer data (reads trial data per session; one-time)...")
        data = ExplorerData(**build_kwargs).build()

    if len(data.df) == 0:
        print("No data to explore — run compute_estim_neighbor_scores first, or "
              "widen the session/trial-type selection.")
        return

    nb_values = data.available_n_neighbors or [3]
    default_nb = 3 if 3 in nb_values else nb_values[0]
    data.set_n_neighbors(default_nb)

    root = tk.Tk()
    root.title("EStim isolation-vs-effect explorer")
    root.geometry("1150x820")

    controls = ttk.Frame(root, padding=8)
    controls.pack(side=tk.TOP, fill=tk.X)

    x_options = build_x_options(data)
    x_by_label = {opt.label: opt for opt in x_options}

    split_opts = available_split_options(data.df)
    split_labels = [lbl for lbl, _ in split_opts]
    split_col_by_label = dict(split_opts)

    trial_type_values = ['All (pooled)'] + list(data.trial_types)

    # --- control variables ---
    metric_var = tk.StringVar(value=x_options[0].label)
    agg_var = tk.StringVar(value='mean')
    trial_var = tk.StringVar(value=trial_type_values[0])
    split_var = tk.StringVar(value=split_labels[0])
    nb_var = tk.StringVar(value=str(default_nb))
    abs_var = tk.BooleanVar(value=iso.COMPARISON_ABS_EFFECT)
    color_var = tk.BooleanVar(value=True)
    status_var = tk.StringVar(value="")

    def _add_labeled(parent, text, widget):
        col = ttk.Frame(parent)
        ttk.Label(col, text=text, font=('TkDefaultFont', 8)).pack(anchor='w')
        widget.pack(anchor='w')
        col.pack(side=tk.LEFT, padx=6)

    metric_cb = ttk.Combobox(controls, textvariable=metric_var, state='readonly',
                             values=[opt.label for opt in x_options], width=28)
    agg_cb = ttk.Combobox(controls, textvariable=agg_var, state='readonly',
                          values=list(AGGREGATIONS), width=8)
    trial_cb = ttk.Combobox(controls, textvariable=trial_var, state='readonly',
                            values=trial_type_values, width=22)
    split_cb = ttk.Combobox(controls, textvariable=split_var, state='readonly',
                            values=split_labels, width=18)
    nb_cb = ttk.Combobox(controls, textvariable=nb_var, state='readonly',
                         values=[str(v) for v in nb_values], width=6)

    _add_labeled(controls, "metric (X axis)", metric_cb)
    _add_labeled(controls, "aggregation", agg_cb)
    _add_labeled(controls, "trial type", trial_cb)
    _add_labeled(controls, "split by", split_cb)
    _add_labeled(controls, "n_neighbors", nb_cb)

    checks = ttk.Frame(controls)
    ttk.Checkbutton(checks, text="|effect|", variable=abs_var).pack(anchor='w')
    ttk.Checkbutton(checks, text="colour by session", variable=color_var).pack(anchor='w')
    checks.pack(side=tk.LEFT, padx=6)

    fig = Figure(figsize=(9, 6.4))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    NavigationToolbar2Tk(canvas, root)  # pan/zoom/save toolbar

    ttk.Label(root, textvariable=status_var, anchor='w',
              relief=tk.SUNKEN).pack(side=tk.BOTTOM, fill=tk.X)

    def redraw(*_):
        try:
            x_option = x_by_label[metric_var.get()]
            # Aggregation only applies to neighbour metrics.
            agg_cb.configure(state='readonly' if x_option.uses_aggregation else 'disabled')
            aggregation = agg_var.get()
            tt = trial_var.get()
            trial_type = None if tt == 'All (pooled)' else tt
            split_col = split_col_by_label.get(split_var.get())

            draw_explorer_plot(
                fig, data.df, x_option, aggregation=aggregation,
                trial_type=trial_type, split_col=split_col,
                abs_effect=abs_var.get(), color_by_session=color_var.get(),
                min_on_trials=iso.COMPARISON_MIN_ON_TRIALS,
                min_off_trials=iso.COMPARISON_MIN_OFF_TRIALS)
            fig.tight_layout()
            canvas.draw_idle()
            status_var.set(
                f"metric={x_option.label} | agg="
                f"{aggregation if x_option.uses_aggregation else 'n/a'} | "
                f"trial_type={tt} | split={split_var.get()} | "
                f"n_neighbors={data.n_neighbors} | rows={len(data.df)}")
        except Exception as exc:
            traceback.print_exc()
            status_var.set(f"ERROR: {exc}")

    def on_nb_change(*_):
        status_var.set("Re-joining neighbour scores...")
        root.update_idletasks()
        metric_names = data.set_n_neighbors(int(nb_var.get()))
        # Rebuild X options in case the metric set changed; keep selection if valid.
        nonlocal x_options, x_by_label
        x_options = build_x_options(data)
        x_by_label = {opt.label: opt for opt in x_options}
        metric_cb.configure(values=[opt.label for opt in x_options])
        if metric_var.get() not in x_by_label:
            metric_var.set(x_options[0].label)
        redraw()

    for cb in (metric_cb, agg_cb, trial_cb, split_cb):
        cb.bind('<<ComboboxSelected>>', redraw)
    nb_cb.bind('<<ComboboxSelected>>', on_nb_change)
    abs_var.trace_add('write', redraw)
    color_var.trace_add('write', redraw)

    redraw()
    root.mainloop()


def main():
    """Launch the explorer using the shared COMPARISON_* config (same session /
    trial-type selection as the static analysis)."""
    # The explorer always keeps trial_type as a live dimension, so an explicit
    # COMPARISON_TRIAL_TYPES list is used as-is; None or [] auto-discovers the
    # trial types present in the selected sessions.
    trial_types = COMPARISON_TRIAL_TYPES or None
    launch_gui(
        metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        trial_types=trial_types,
        exclude_other_estim=True,
    )


if __name__ == '__main__':
    main()

"""
Tuning-curve-style plot: current spread vs the geometry of tuning.

The isolation leaderboard/heatmaps in ``analyze_estim_isolation_effect`` answer
"which tuning-geometry metric best predicts the estim effect?" — but they bury
the more basic question the whole project rests on: **as you drive more current,
does the stimulated tissue's tuning stay locally similar, or does the tuning
neighbourhood you're perturbing get larger?**

This module makes that relationship explicit, one point per estim spec
(condition) — each spec delivers its OWN current, so we do NOT average specs
within an experiment (that would collapse the very current variation the X-axis
shows). Set aggregate_by='experiment' if you deliberately want per-experiment
means instead.

    X = a current metric per spec, set by X_METRIC (default 'total_current_uA' =
        a1 × num_channels; or 'current_per_second' = a1 × num_channels ×
        pulse_rate_hz; or 'n_active_channels')
    Y = tuning similarity of each estim channel to its physical neighbours on the
        probe (Spearman rho of ga_mean_response, the ``channel_corr`` metric),
        averaged over the spec's estim channels.

Three tuning families x three probe scales, laid out as a grid so you can read
how the picture changes from a local patch to the whole probe:

    rows  (tuning family):
      - mean corr        mean rho to the N nearest neighbours (how similar, on
                         average, is the surrounding tissue)
      - max corr         the single most-similar of the N nearest (is there ANY
                         highly-similar neighbour nearby)
      - area high corr   fraction of the N nearest with rho > threshold (how much
                         of the neighbourhood is highly similar — the "area of
                         probe with high correlation")
    cols  (probe scale, = n_neighbors):
      - local       n=4    a tight patch around the estim site
      - half-probe  n=16
      - whole-probe n=32   effectively the whole probe (<=32 channels)

Each panel is one point per spec (filtered to a trial type), coloured by the
estim effect on behaviour (ON − OFF %): red = positive, blue = negative, on a
symmetric scale shared across panels. So a panel reads as "where in
current-spread × tuning space do the effects land, and which way do they point"
— no line is fit.

The tuning metric is trial-type-independent (it comes from GA responses, not
behaviour); filtering by trial type only selects WHICH specs (those actually
delivered in that trial type) enter the plot, so you compare like with like
against the effect analyses.

All plots also split by polarity (anodic = PositiveFirst / cathodic =
NegativeFirst) by default (by_polarity=True): the tuning grid emits a separate
figure per (trial_type, polarity), and the half-distance plot puts polarity on
its rows and trial types on its columns. Set by_polarity=False to pool.

Run this file (uses the shared COMPARISON_* config in
analyze_estim_isolation_effect). Needs the GA response vectors that
compute_estim_neighbor_scores reads — but computes the correlations directly, so
it does NOT depend on EStimNeighborScores having been populated.
"""

import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis import analyze_estim_isolation_effect as iso
from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
    _discover_trial_types,
    _effect_and_current_table,
    _fetch_estim_power_and_polarity,
    _rc_for_trial_type,
    _slug,
    COMPARISON_METRIC,
    COMPARISON_REQUIRED_CONDITIONS,
    COMPARISON_START_SESSION_ID,
    COMPARISON_EXCLUDE_SESSION_IDS,
    COMPARISON_MIN_ON_TRIALS,
    COMPARISON_TRIAL_TYPES,
    COMPARISON_SAVE_DIR,
)
from src.analysis.nafc.group_analysis.compute_estim_neighbor_scores import (
    channel_to_str,
    precompute_neighbor_order,
    prepare_session_metrics,
    _physical_neighbors,
)
from src.cluster.cluster_isolation_score import fetch_active_estim_channels_by_spec
from clat.util.connection import Connection

# The stored channel-correlation metric (Spearman rho of ga_mean_response vectors)
# whose per-pair values we re-aggregate three ways.
CORR_METRIC_NAME = 'channel_corr'

# Row-split categories. Polarity (anodic = PositiveFirst leading anodic phase /
# cathodic = NegativeFirst) and waveform 'shape' (Biphasic vs
# BiphasicWithInterphaseDelay). Orders fix the panel order; SHORT maps give the
# panel labels.
POLARITY_ORDER = ('PositiveFirst', 'NegativeFirst')
POLARITY_SHORT = {'PositiveFirst': 'anodic', 'NegativeFirst': 'cathodic'}
WAVEFORM_ORDER = ('Biphasic', 'BiphasicWithInterphaseDelay')
WAVEFORM_SHORT = {'Biphasic': 'biphasic',
                  'BiphasicWithInterphaseDelay': 'biphasic+delay',
                  'Triphasic': 'triphasic'}
# Categorical row-split columns: column -> (value order, short-label map).
ROW_SPLIT_ORDERS = {'polarity': POLARITY_ORDER, 'waveform': WAVEFORM_ORDER}
ROW_SPLIT_SHORT = {'polarity': POLARITY_SHORT, 'waveform': WAVEFORM_SHORT}


def _pol_short(polarity):
    return POLARITY_SHORT.get(polarity, str(polarity))


def _value_short(col, value):
    return ROW_SPLIT_SHORT.get(col, {}).get(value, str(value))


def _present_polarities(df):
    """Polarity values present in df, anodic then cathodic, then any others; None
    excluded."""
    return _present_values(df, 'polarity')


def _present_values(df, col):
    """Distinct values of `col` present in df, in the column's defined order first,
    then any others; None excluded."""
    order = ROW_SPLIT_ORDERS.get(col, ())
    present = [v for v in order if (df[col] == v).any()]
    others = [v for v in df[col].dropna().unique().tolist() if v not in order]
    return present + others


def _row_groups(points, row_cols):
    """Ordered list of {col: value} dicts, one per present combination of the
    row-split columns (e.g. polarity × waveform). Empty [] of cols -> [{}]."""
    row_cols = [c for c in row_cols if c in points.columns and points[c].notna().any()]
    if not row_cols:
        return [{}], row_cols
    groups = [{}]
    for col in row_cols:
        vals = _present_values(points, col)
        groups = [dict(g, **{col: v}) for g in groups for v in vals]
    # keep only combinations that actually have rows
    groups = [g for g in groups
              if len(_filter_rows(points, g)) > 0]
    return (groups or [{}]), row_cols


def _filter_rows(points, group):
    sub = points
    for col, val in group.items():
        sub = sub[sub[col] == val]
    return sub


def _row_label(group, row_cols):
    """' · '-joined short labels for a row combination, e.g. 'ANODIC · BIPHASIC'."""
    return " · ".join(_value_short(c, group[c]).upper() for c in row_cols if c in group)


def _fetch_estim_shape(session_ids):
    """{(session_id, estim_spec_id): shape} from EStimParameters (active channels).
    shape is the waveform ENUM: Biphasic / BiphasicWithInterphaseDelay / Triphasic."""
    conn = Connection("allen_data_repository")
    base = ("SELECT session_id, estim_spec_id, MIN(shape) AS shape "
            "FROM EStimParameters WHERE a1 > 0")
    if session_ids:
        placeholders = ', '.join(['%s'] * len(session_ids))
        conn.execute(f"{base} AND session_id IN ({placeholders}) "
                     "GROUP BY session_id, estim_spec_id", tuple(session_ids))
    else:
        conn.execute(f"{base} GROUP BY session_id, estim_spec_id")
    return {(s, int(spec)): shape for s, spec, shape in conn.fetch_all()}


def _attach_estim_metrics(df):
    """Add per-spec 'polarity', 'total_current_uA' (= Σ a1 over active channels =
    a1 × num_channels), and 'waveform' (shape) columns from EStimParameters, in
    place; returns df."""
    session_ids = sorted(df['session_id'].unique().tolist())
    power = _fetch_estim_power_and_polarity(session_ids)
    df['polarity'] = [
        (power.get((s, int(spec)), {}) or {}).get('polarity')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    df['total_current_uA'] = [
        (power.get((s, int(spec)), {}) or {}).get('total_current_uA')
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    shapes = _fetch_estim_shape(session_ids)
    df['waveform'] = [
        shapes.get((s, int(spec))) for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    # Frequency: current_per_second = total_current × pulse_rate, so
    # pulse_rate_hz = current_per_second / total_current_uA (NaN when total is 0/missing).
    cps = pd.to_numeric(df.get('current_per_second'), errors='coerce').to_numpy(dtype=float)
    tot = pd.to_numeric(df.get('total_current_uA'), errors='coerce').to_numpy(dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        df['pulse_rate_hz'] = np.where(tot > 0, cps / tot, np.nan)
    return df

# Tuning families (rows). Each is a different aggregation of the same per-neighbour
# correlations. Order here is the row order in the figure.
FAMILY_MEAN = 'mean_corr'
FAMILY_MAX = 'max_corr'
FAMILY_AREA = 'area_high_corr'
FAMILIES = (FAMILY_MEAN, FAMILY_MAX, FAMILY_AREA)

FAMILY_LABELS = {
    FAMILY_MEAN: 'mean neighbour corr',
    FAMILY_MAX: 'max neighbour corr',
    FAMILY_AREA: 'area of high corr',  # threshold appended at plot time
}

# Probe scales (columns): display label -> n_neighbors. Sorted by n at plot time.
DEFAULT_SCALES = {
    'local (n=4)': 4,
    'half-probe (n=16)': 16,
    'whole-probe (n=32)': 32,
}

# rho above this counts as "highly correlated" for the area family.
DEFAULT_HIGH_CORR_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# X-axis current metric. Change X_METRIC to switch what "current spread" means on
# the X axis of EVERY plot in this module (scatter, half-distance, heatmaps).
#   'current_per_second' = a1 × num_channels × pulse_rate_hz (µA·Hz) — dose rate
#   'total_current_uA'   = a1 × num_channels (µA) — "current × num_channels"
#   'n_active_channels'  = number of active stim channels
# All three columns are attached to the tables, so switching needs only this edit.
# ---------------------------------------------------------------------------
X_METRIC = 'current_per_second'
X_LABELS = {
    'current_per_second': 'current_per_second (µA·Hz)',
    'total_current_uA': 'total current  (a1 × num_channels, µA)',
    'pulse_rate_hz': 'pulse rate / frequency (Hz)',
    'n_active_channels': 'num active channels',
}
# Current columns retained on every points table (so any can be selected as X).
# pulse_rate_hz = current_per_second / total_current_uA (their product is the dose
# rate), so total current and frequency are self-consistent decompositions of it.
CURRENT_COLUMNS = ('current_per_second', 'total_current_uA', 'pulse_rate_hz',
                   'n_active_channels')

X_COLUMN = X_METRIC
X_LABEL = X_LABELS.get(X_METRIC, X_METRIC)


def _metric_col(family, n_neighbors):
    return f"{family}__n{int(n_neighbors)}"


# ---------------------------------------------------------------------------
# Shared axis limits — computed once from the whole points table so every panel
# (and every separate polarity / trial-type figure) uses identical x/y limits and
# is directly comparable.
# ---------------------------------------------------------------------------

def _axis_limits(series, pad=0.05):
    """(lo, hi) padded limits over the finite values of `series`, or None."""
    v = pd.to_numeric(series, errors='coerce')
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return None
    lo, hi = float(v.min()), float(v.max())
    if lo == hi:
        d = abs(lo) or 1.0
        return (lo - 0.5 * d, hi + 0.5 * d)
    m = (hi - lo) * pad
    return (lo - m, hi + m)


def _family_ylims(points, scales):
    """{family: (lo, hi)} y-limits per tuning family, pooled across its scale
    columns, so every panel in a family row shares one Y scale."""
    out = {}
    for fam in FAMILIES:
        cols = [_metric_col(fam, n) for n in scales.values()
                if _metric_col(fam, n) in points.columns]
        if not cols:
            continue
        vals = pd.concat([pd.to_numeric(points[c], errors='coerce') for c in cols],
                         ignore_index=True)
        lim = _axis_limits(vals)
        if lim:
            out[fam] = lim
    return out


# ---------------------------------------------------------------------------
# Per-session tuning computation
# ---------------------------------------------------------------------------

def _spec_tuning_at_scales(corr_metric, estim_channels, channels_with_data, coords,
                           neighbor_order, scales, threshold, *,
                           exclude_other_estim=True):
    """For one estim spec, aggregate the estim channels' neighbour correlations into
    {mean_corr__nN, max_corr__nN, area_high_corr__nN} for each scale N.

    For each actively-stimulating channel we take its N physically-nearest
    neighbours (excluding the spec's other estim channels, matching
    ``exclude_other_estim=True`` elsewhere) and their Spearman rho, then:
      mean_corr = mean rho,  max_corr = max rho,
      area_high_corr = fraction of neighbours with rho > threshold.
    The spec's value is the mean across its estim channels."""
    n_source = scales.values() if isinstance(scales, dict) else scales
    n_values = sorted(set(int(n) for n in n_source))
    max_n = n_values[-1]
    estim_set = set(estim_channels)
    exclude = estim_set if exclude_other_estim else set()

    per_channel = {_metric_col(fam, n): [] for fam in FAMILIES for n in n_values}
    for e in estim_channels:
        if e not in channels_with_data:
            continue  # estim channel has no response data
        e_str = channel_to_str(e)
        # Nearest -> farthest, up to the largest scale; slice for smaller scales.
        neighbors = _physical_neighbors(e, channels_with_data, coords, max_n,
                                        exclude, neighbor_order=neighbor_order)
        rhos_ordered = [corr_metric.pair_similarity(e_str, channel_to_str(nb))
                        for nb in neighbors]
        for n in n_values:
            rhos = np.asarray([r for r in rhos_ordered[:n]
                               if r is not None and np.isfinite(r)], dtype=float)
            if rhos.size == 0:
                continue
            per_channel[_metric_col(FAMILY_MEAN, n)].append(float(rhos.mean()))
            per_channel[_metric_col(FAMILY_MAX, n)].append(float(rhos.max()))
            per_channel[_metric_col(FAMILY_AREA, n)].append(
                float(np.mean(rhos > threshold)))

    return {col: (float(np.mean(vals)) if vals else None)
            for col, vals in per_channel.items()}


def compute_session_tuning_metrics(session_id, scales, threshold, *,
                                   exclude_other_estim=True):
    """{estim_spec_id: {metric_col: value}} for one session, or {} if the session
    can't be prepared or has no channel-correlation metric. Trial-type independent."""
    metrics, channels_with_data, coords = prepare_session_metrics(session_id)
    if metrics is None:
        return {}
    corr_metric = next((m for m in metrics if m.name == CORR_METRIC_NAME), None)
    if corr_metric is None:
        print(f"  {session_id}: no '{CORR_METRIC_NAME}' metric available; skipping")
        return {}
    neighbor_order = precompute_neighbor_order(channels_with_data, coords)
    estim_by_spec = fetch_active_estim_channels_by_spec(session_id)
    out = {}
    for spec_id, estim_channels in estim_by_spec.items():
        out[int(spec_id)] = _spec_tuning_at_scales(
            corr_metric, estim_channels, channels_with_data, coords,
            neighbor_order, scales, threshold,
            exclude_other_estim=exclude_other_estim)
    return out


# ---------------------------------------------------------------------------
# Table building + per-experiment aggregation
# ---------------------------------------------------------------------------

def build_current_spread_tuning_table(trial_types, *, start_session_id=None,
                                      exclude_session_ids=None,
                                      effect_metric=COMPARISON_METRIC,
                                      base_required_conditions=None,
                                      scales=DEFAULT_SCALES,
                                      threshold=DEFAULT_HIGH_CORR_THRESHOLD,
                                      exclude_other_estim=True,
                                      min_on_trials=COMPARISON_MIN_ON_TRIALS):
    """Per-(session, estim_spec, trial_type) table with current_per_second and the
    tuning-metric columns. Specs enter a trial type only if they were delivered in
    it with >= min_on_trials estim-ON trials.

    Returns (df, metric_cols). Tuning metrics are computed once per session and
    reused across trial types (they don't depend on trial type)."""
    metric_cols = [_metric_col(fam, n) for fam in FAMILIES
                   for n in sorted(set(int(v) for v in scales.values()))]

    frames = []
    for tt in trial_types:
        rc = _rc_for_trial_type(base_required_conditions, tt)
        print(f"\n--- current/spec membership for trial_type={tt!r} ---")
        df_tt = _effect_and_current_table(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=effect_metric, required_conditions=rc)
        if len(df_tt) == 0:
            print(f"  (no specs for trial_type={tt!r})")
            continue
        df_tt = df_tt[df_tt['n_on'] >= min_on_trials].copy()
        df_tt['trial_type'] = tt
        frames.append(df_tt)

    if not frames:
        return pd.DataFrame(), metric_cols
    df = pd.concat(frames, ignore_index=True)
    _attach_estim_metrics(df)

    tuning_by_session = {}
    for sid in sorted(df['session_id'].unique().tolist()):
        print(f"\n=== tuning metrics for session {sid} ===")
        tuning_by_session[sid] = compute_session_tuning_metrics(
            sid, scales, threshold, exclude_other_estim=exclude_other_estim)

    for col in metric_cols:
        df[col] = [
            (tuning_by_session.get(s, {}).get(int(spec), {}) or {}).get(col)
            for s, spec in zip(df['session_id'], df['estim_spec_id'])]

    n_scored = df[metric_cols].notna().any(axis=1).sum()
    print(f"\nBuilt current-spread/tuning table: {len(df)} specs across "
          f"{df['session_id'].nunique()} sessions and {len(frames)} trial types; "
          f"{n_scored} specs have tuning scores")
    return df, metric_cols


def aggregate_per_experiment(df, metric_cols):
    """Collapse the per-spec table to one row per (trial_type, session): mean
    current_per_second, mean estim effect, and mean of each tuning metric across
    the experiment's specs.

    NOTE: this averages away the per-condition current variation within an
    experiment (different specs deliver different currents), so it is NOT the
    default point unit — use it only when you deliberately want one point per
    experiment. See build_points."""
    if len(df) == 0:
        return df
    agg_map = {'effect_size': ('effect_size', 'mean')}
    # Average every available current metric (so X can be any of them).
    agg_map.update({c: (c, 'mean') for c in CURRENT_COLUMNS if c in df.columns})
    agg_map.update({c: (c, 'mean') for c in metric_cols})
    agg_map['n_specs'] = ('estim_spec_id', 'size')
    # Keep the categorical splits as grouping keys so a per-experiment point never
    # mixes anodic/cathodic or biphasic/delay specs.
    group_keys = [k for k in ('trial_type', 'polarity', 'waveform', 'session_id')
                  if k in df.columns]
    return df.groupby(group_keys, as_index=False).agg(**agg_map)


def build_points(df, metric_cols, aggregate_by='spec'):
    """The plotting unit. 'spec' (default) = one point per estim spec/condition,
    keeping each spec's own current, tuning, and effect (this is almost always what
    you want — different specs in an experiment deliver different currents).
    'experiment' collapses to one point per (trial_type, session), averaging those
    away."""
    if aggregate_by == 'experiment':
        return aggregate_per_experiment(df, metric_cols)
    if aggregate_by != 'spec':
        raise ValueError(f"aggregate_by must be 'spec' or 'experiment'; got {aggregate_by!r}")
    keep = (['trial_type', 'polarity', 'waveform', 'session_id', 'estim_spec_id',
             'effect_size'] + list(CURRENT_COLUMNS) + list(metric_cols))
    keep = [c for c in dict.fromkeys(keep) if c in df.columns]  # de-dup, keep order
    return df[keep].copy()


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_current_spread_vs_tuning_for_trial_type(agg_tt, *, scales=DEFAULT_SCALES,
                                                 threshold=DEFAULT_HIGH_CORR_THRESHOLD,
                                                 trial_type='', point_noun='spec',
                                                 xlim=None, ylim_by_family=None,
                                                 vmax=None, output_path=None):
    """Grid of tuning-family (rows) x probe-scale (cols) panels for one trial type.
    One point per `point_noun` (spec/condition by default); X = current_per_second,
    Y = the tuning metric, colour = estim effect. xlim / ylim_by_family (a
    {family: (lo, hi)} dict) / vmax fix the axes and colour scale so separate
    figures are comparable; if None they are computed from this figure's own data."""
    scale_items = sorted(scales.items(), key=lambda kv: kv[1])  # (label, n) low->high
    if xlim is None:
        xlim = _axis_limits(agg_tt[X_COLUMN]) if X_COLUMN in agg_tt.columns else None
    if ylim_by_family is None:
        ylim_by_family = _family_ylims(agg_tt, scales)
    nrows, ncols = len(FAMILIES), len(scale_items)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.6 * ncols, 4.0 * nrows),
                             squeeze=False, constrained_layout=True)

    # Symmetric diverging colour scale for the estim effect (red = positive,
    # blue = negative), shared across every panel.
    if vmax is None:
        vmax = _effect_vmax(agg_tt)

    scatter_ref = None
    for r, family in enumerate(FAMILIES):
        for c, (scale_label, n) in enumerate(scale_items):
            ax = axes[r][c]
            col = _metric_col(family, n)
            sub = agg_tt[[X_COLUMN, col, 'effect_size']].dropna(subset=[X_COLUMN, col])
            x = sub[X_COLUMN].to_numpy(dtype=float)
            y = sub[col].to_numpy(dtype=float)
            eff = pd.to_numeric(sub['effect_size'], errors='coerce').to_numpy(dtype=float)
            has_eff = np.isfinite(eff)

            # Points with no computable effect can't be coloured — show gray.
            if (~has_eff).any():
                ax.scatter(x[~has_eff], y[~has_eff], s=55, alpha=0.6,
                           color='lightgray', edgecolors='gray', linewidths=0.4)
            if has_eff.any():
                sc = ax.scatter(x[has_eff], y[has_eff], c=eff[has_eff], cmap='RdBu_r',
                                vmin=-vmax, vmax=vmax, s=60, alpha=0.9,
                                edgecolors='black', linewidths=0.5)
                scatter_ref = sc

            title_bits = []
            if r == 0:
                title_bits.append(scale_label)
            title_bits.append(f"n={len(x)} {point_noun}s")
            ax.set_title("\n".join(title_bits), fontsize=10)

            if xlim:
                ax.set_xlim(xlim)
            if ylim_by_family and family in ylim_by_family:
                ax.set_ylim(ylim_by_family[family])
            if r == nrows - 1:
                ax.set_xlabel(X_LABEL, fontsize=9)
            if c == 0:
                ylab = FAMILY_LABELS[family]
                if family == FAMILY_AREA:
                    ylab += f" (ρ>{threshold:g})"
                ax.set_ylabel(ylab, fontsize=10)
            ax.grid(True, alpha=0.3)

    if scatter_ref is not None:
        cbar = fig.colorbar(scatter_ref, ax=axes.ravel().tolist(), shrink=0.6,
                            pad=0.02)
        cbar.set_label('estim effect (ON − OFF %)  — red = positive, blue = negative',
                       fontsize=10)

    fig.suptitle(f"Current spread vs tuning geometry — one point per {point_noun} "
                 f"(colour = estim effect)"
                 f"{('  [' + str(trial_type) + ']') if trial_type else ''}",
                 fontsize=14, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved current-spread/tuning plot to {output_path}")
    plt.show()
    return fig


# ---------------------------------------------------------------------------
# End-to-end runner
# ---------------------------------------------------------------------------

def run_current_spread_vs_tuning(trial_types=None, *, start_session_id=None,
                                 exclude_session_ids=None,
                                 effect_metric=COMPARISON_METRIC,
                                 base_required_conditions=None,
                                 scales=DEFAULT_SCALES,
                                 threshold=DEFAULT_HIGH_CORR_THRESHOLD,
                                 exclude_other_estim=True,
                                 min_on_trials=COMPARISON_MIN_ON_TRIALS,
                                 aggregate_by='spec', by_polarity=True, save_dir=None):
    """Build the table and draw one figure per trial type. trial_types=None
    auto-discovers them. aggregate_by='spec' (default) plots one point per estim
    spec/condition (keeps each condition's own current); 'experiment' averages per
    session. by_polarity=True draws a separate figure per (trial_type, polarity)
    — anodic vs cathodic. Returns (per_spec_df, points_df)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] CURRENT-SPREAD vs TUNING  trial_types={trial_types}  "
          f"effect_metric={effect_metric}  scales={scales}  threshold={threshold}  "
          f"min_on={min_on_trials}  point={aggregate_by}  by_polarity={by_polarity}")

    df, metric_cols = build_current_spread_tuning_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions, scales=scales,
        threshold=threshold, exclude_other_estim=exclude_other_estim,
        min_on_trials=min_on_trials)
    if len(df) == 0:
        print("Nothing to plot.")
        return df, pd.DataFrame()

    points = build_points(df, metric_cols, aggregate_by)
    # Shared limits + colour scale from ALL points so every (trial_type, polarity)
    # figure matches.
    xlim = _axis_limits(points[X_COLUMN])
    ylim_by_family = _family_ylims(points, scales)
    vmax = _effect_vmax(points)
    polarities = (_present_polarities(points)
                  if (by_polarity and points['polarity'].notna().any()) else [None])
    for tt in trial_types:
        for pol in polarities:
            pts_tt = points[points['trial_type'] == tt]
            if pol is not None:
                pts_tt = pts_tt[pts_tt['polarity'] == pol]
            if len(pts_tt) == 0:
                continue
            tag = tt + (f"  [{_pol_short(pol)}]" if pol is not None else "")
            print(f"\n=== {tag}: {len(pts_tt)} {aggregate_by}s ===")
            fname = f"tuning_vs_{_slug(X_COLUMN)}_{_slug(tt)}" + \
                    (f"_{_pol_short(pol)}" if pol is not None else "") + ".png"
            out_path = os.path.join(save_dir, fname) if save_dir else None
            plot_current_spread_vs_tuning_for_trial_type(
                pts_tt, scales=scales, threshold=threshold, trial_type=tag,
                point_noun=aggregate_by, xlim=xlim, ylim_by_family=ylim_by_family,
                vmax=vmax, output_path=out_path)
    return df, points


# ---------------------------------------------------------------------------
# "How far does high correlation spread": correlation half-distance
#
# For each spec we pool the (physical distance, rho) pairs from all its estim
# channels to their probe neighbours, bin rho by distance, and read off the
# distance at which rho decays to halfway between its near-field level and its
# far-field baseline. Because it is measured RELATIVE to each spec's own near/far
# levels, it captures how far similarity REACHES, not how strong it is locally
# (which is always higher near the site) — the metric the argmax idea couldn't.
# ---------------------------------------------------------------------------

HALFDIST_COL = 'corr_half_distance_um'
# Far-field baseline = mean rho over this fraction of the farthest distance bins.
DEFAULT_FAR_FRACTION = 0.25
# Near-field level = mean rho over this many nearest distance bins.
DEFAULT_NEAR_BINS = 1
# Per-distance-bin summary: 'median' is robust to one anomalously low/high channel
# in a bin; 'mean' is the plain average.
DEFAULT_BIN_AGG = 'median'
# How the half-crossing is read off the ρ-vs-distance profile — the noise-robustness
# method:
#   'sustained' (default) — the profile must stay below half_level for
#       DEFAULT_PERSIST_BINS consecutive bins to count as the crossing, so a single
#       nearby channel that dips and recovers (tuning actually wide) is ignored.
#   'isotonic'  — fit a monotone non-increasing curve first, then first crossing.
#       Clean, but a low NEAR channel forces later bins down and can under-estimate.
#   'none'      — raw bins, first crossing (original, most noise-sensitive).
DEFAULT_SMOOTHING = 'sustained'
# Consecutive below-half bins required for a 'sustained' crossing.
DEFAULT_PERSIST_BINS = 2


def _isotonic_nonincreasing(values, weights):
    """Weighted isotonic regression enforcing a NON-INCREASING fit via
    pool-adjacent-violators. Correlation is expected to fall with distance, so this
    encodes that prior and pools any local increase (e.g. one low nearby channel
    surrounded by high ones) into its neighbours — smoothing out noise without a
    window size. Returns a non-increasing array the same length as `values`."""
    sums, wts, lens = [], [], []   # per block: sum(w*y), sum(w), #bins
    for y, w in zip(values, weights):
        w = float(w) if (w and w > 0) else 1e-9
        sums.append(float(y) * w)
        wts.append(w)
        lens.append(1)
        while len(sums) >= 2 and (sums[-2] / wts[-2]) < (sums[-1] / wts[-1]):
            s, w2, length = sums.pop(), wts.pop(), lens.pop()
            sums[-1] += s
            wts[-1] += w2
            lens[-1] += length
    out = []
    for s, w, length in zip(sums, wts, lens):
        out.extend([s / w] * length)
    return np.asarray(out, dtype=float)


def _probe_pitch(coords):
    """Smallest nonzero inter-channel distance (probe electrode spacing, µm), used
    as the distance-bin width. Falls back to 1.0 if undefined."""
    chans = list(coords)
    xy = np.asarray([coords[c] for c in chans], dtype=float)
    best = np.inf
    for i in range(len(chans)):
        d = np.linalg.norm(xy - xy[i], axis=1)
        d = d[d > 0]
        if len(d):
            best = min(best, float(d.min()))
    return best if np.isfinite(best) else 1.0


def _half_distance_for_spec(corr_metric, estim_channels, channels_with_data, coords,
                            *, exclude_other_estim=True, pitch=1.0,
                            far_fraction=DEFAULT_FAR_FRACTION, near_bins=DEFAULT_NEAR_BINS,
                            bin_agg=DEFAULT_BIN_AGG, smoothing=DEFAULT_SMOOTHING):
    """Correlation half-distance (µm) for one spec, or None if undefined.

    Pool (distance, rho) over the spec's estim channels -> other probe channels and
    bin rho by distance (width = pitch). Each bin is summarised by `bin_agg`
    ('median' = robust to one bad channel, 'mean' = plain). Then:
      near_level = mean over the nearest `near_bins` (profile) bins
      baseline   = mean over the farthest `far_fraction` of bins
      half_level = baseline + 0.5 * (near_level - baseline)
    d_half = the (interpolated) distance where the profile falls to half_level. The
    crossing rule is set by `smoothing`:
      'sustained' (default) — must stay below half for DEFAULT_PERSIST_BINS
          consecutive bins, so a single dip that recovers (noisy channel, wide
          tuning) is ignored;
      'isotonic' — fit a monotone non-increasing profile first, then first crossing;
      'none' — raw first crossing.
    If it never crosses within the probe, the probe's max distance is returned
    (spread >= probe). None if near_level <= baseline (no decay) or too few points."""
    estim_set = set(estim_channels)
    exclude = estim_set if exclude_other_estim else set()

    dists, rhos = [], []
    for e in estim_channels:
        if e not in channels_with_data:
            continue
        e_str = channel_to_str(e)
        e_xy = coords[e]
        for c in channels_with_data:
            if c == e or c in exclude:
                continue
            rho = corr_metric.pair_similarity(e_str, channel_to_str(c))
            if rho is None or not np.isfinite(rho):
                continue
            dists.append(float(np.linalg.norm(coords[c] - e_xy)))
            rhos.append(float(rho))
    if len(dists) < 3:
        return None
    dists = np.asarray(dists, dtype=float)
    rhos = np.asarray(rhos, dtype=float)

    if not pitch or pitch <= 0:
        pitch = 1.0
    edges = np.arange(0.0, dists.max() + pitch, pitch)
    if len(edges) < 3:
        return None
    centers = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(dists, edges) - 1, 0, len(centers) - 1)
    summarise = np.median if bin_agg == 'median' else np.mean
    prof = np.array([summarise(rhos[idx == k]) if np.any(idx == k) else np.nan
                     for k in range(len(centers))])
    counts = np.array([int(np.sum(idx == k)) for k in range(len(centers))])
    valid = np.isfinite(prof)
    centers_v, prof_v, counts_v = centers[valid], prof[valid], counts[valid]
    if len(prof_v) < 3:
        return None

    # Optional monotone fit (weighted by bin counts, so sparse far bins count less).
    if smoothing == 'isotonic':
        prof_v = _isotonic_nonincreasing(prof_v, counts_v)

    near_level = float(prof_v[:max(1, near_bins)].mean())
    n_far = max(1, int(round(far_fraction * len(prof_v))))
    baseline = float(prof_v[-n_far:].mean())
    if not (np.isfinite(near_level) and np.isfinite(baseline)) or near_level <= baseline:
        return None

    half_level = baseline + 0.5 * (near_level - baseline)
    below = prof_v <= half_level
    n = len(prof_v)

    if smoothing == 'sustained':
        # The crossing must persist for several bins, so one bin that dips below
        # half and recovers (a lone noisy channel, tuning actually wide) is ignored.
        persist = min(max(1, DEFAULT_PERSIST_BINS), n)
        cross = next((i for i in range(n) if below[i:i + persist].all()), None)
    else:  # 'isotonic' (monotone -> unique) or 'none': first bin below half
        nz = np.where(below)[0]
        cross = int(nz[0]) if nz.size else None

    if cross is None:
        return float(centers_v[-1])  # never sustained-crosses within the probe
    # Interpolate between the last bin above half and the crossing bin.
    above = np.where(prof_v[:cross] > half_level)[0]
    if above.size == 0:
        return float(centers_v[cross])
    a = int(above[-1])
    x0, x1 = centers_v[a], centers_v[cross]
    y0, y1 = prof_v[a], prof_v[cross]
    if y0 == y1:
        return float(x1)
    return float(x0 + (half_level - y0) * (x1 - x0) / (y1 - y0))


def compute_session_half_distance(session_id, *, exclude_other_estim=True,
                                  far_fraction=DEFAULT_FAR_FRACTION,
                                  near_bins=DEFAULT_NEAR_BINS,
                                  bin_agg=DEFAULT_BIN_AGG, smoothing=DEFAULT_SMOOTHING):
    """{estim_spec_id: correlation half-distance (µm) or None} for one session."""
    metrics, channels_with_data, coords = prepare_session_metrics(session_id)
    if metrics is None:
        return {}
    corr_metric = next((m for m in metrics if m.name == CORR_METRIC_NAME), None)
    if corr_metric is None:
        print(f"  {session_id}: no '{CORR_METRIC_NAME}' metric available; skipping")
        return {}
    pitch = _probe_pitch(coords)
    estim_by_spec = fetch_active_estim_channels_by_spec(session_id)
    out = {}
    for spec_id, estim_channels in estim_by_spec.items():
        out[int(spec_id)] = _half_distance_for_spec(
            corr_metric, estim_channels, channels_with_data, coords,
            exclude_other_estim=exclude_other_estim, pitch=pitch,
            far_fraction=far_fraction, near_bins=near_bins,
            bin_agg=bin_agg, smoothing=smoothing)
    return out


def build_current_spread_halfdist_table(trial_types, *, start_session_id=None,
                                        exclude_session_ids=None,
                                        effect_metric=COMPARISON_METRIC,
                                        base_required_conditions=None,
                                        exclude_other_estim=True,
                                        min_on_trials=COMPARISON_MIN_ON_TRIALS,
                                        far_fraction=DEFAULT_FAR_FRACTION,
                                        near_bins=DEFAULT_NEAR_BINS,
                                        bin_agg=DEFAULT_BIN_AGG,
                                        smoothing=DEFAULT_SMOOTHING):
    """Per-(session, estim_spec, trial_type) table with current_per_second, estim
    effect, and the correlation half-distance. Returns the DataFrame (empty if
    nothing matched)."""
    frames = []
    for tt in trial_types:
        rc = _rc_for_trial_type(base_required_conditions, tt)
        print(f"\n--- current/spec membership for trial_type={tt!r} ---")
        df_tt = _effect_and_current_table(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=effect_metric, required_conditions=rc)
        if len(df_tt) == 0:
            print(f"  (no specs for trial_type={tt!r})")
            continue
        df_tt = df_tt[df_tt['n_on'] >= min_on_trials].copy()
        df_tt['trial_type'] = tt
        frames.append(df_tt)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    _attach_estim_metrics(df)

    hd_by_session = {}
    for sid in sorted(df['session_id'].unique().tolist()):
        print(f"\n=== correlation half-distance for session {sid} ===")
        hd_by_session[sid] = compute_session_half_distance(
            sid, exclude_other_estim=exclude_other_estim,
            far_fraction=far_fraction, near_bins=near_bins,
            bin_agg=bin_agg, smoothing=smoothing)

    df[HALFDIST_COL] = [
        hd_by_session.get(s, {}).get(int(spec))
        for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    n_scored = df[HALFDIST_COL].notna().sum()
    print(f"\nBuilt half-distance table: {len(df)} specs across "
          f"{df['session_id'].nunique()} sessions; {n_scored} have a half-distance")
    return df


def _resolve_row_cols(points, by_polarity, by_waveform):
    """Row-split columns from the by_* flags, keeping only those present with data."""
    wanted = []
    if by_polarity:
        wanted.append('polarity')
    if by_waveform:
        wanted.append('waveform')
    return [c for c in wanted
            if c in points.columns and points[c].notna().any()]


def plot_metric_vs_current_by_trialtype(points, y_col, *, y_label, title,
                                        trial_types, by_polarity=True,
                                        by_waveform=False, point_noun='spec',
                                        x_col=X_COLUMN, x_label=X_LABEL,
                                        output_path=None):
    """Grid of X = x_col vs Y = y_col, colour = estim effect (RdBu_r, symmetric).
    Columns = trial types; rows = every present combination of the categorical
    splits — polarity (by_polarity) × waveform (by_waveform). Generic scatter used
    by the half-distance (and any other single-Y) current-spread plot."""
    tts = [tt for tt in trial_types if (points['trial_type'] == tt).any()]
    if not tts:
        print("No trial types with points to plot.")
        return None
    row_cols = _resolve_row_cols(points, by_polarity, by_waveform)
    groups, row_cols = _row_groups(points, row_cols)

    ncols, nrows = len(tts), len(groups)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 4.4 * nrows),
                             squeeze=False, constrained_layout=True)

    vmax = _effect_vmax(points)
    # Shared limits across every panel (all trial types / row splits).
    xlim = _axis_limits(points[x_col])
    ylim = _axis_limits(points[y_col])

    scatter_ref = None
    for r, group in enumerate(groups):
        for c, tt in enumerate(tts):
            ax = axes[r][c]
            sub = _filter_rows(points[points['trial_type'] == tt], group)
            sub = sub[[x_col, y_col, 'effect_size']].dropna(subset=[x_col, y_col])
            x = sub[x_col].to_numpy(dtype=float)
            y = sub[y_col].to_numpy(dtype=float)
            eff = pd.to_numeric(sub['effect_size'], errors='coerce').to_numpy(dtype=float)
            has_eff = np.isfinite(eff)

            if (~has_eff).any():
                ax.scatter(x[~has_eff], y[~has_eff], s=45, alpha=0.6, color='lightgray',
                           edgecolors='gray', linewidths=0.4)
            if has_eff.any():
                sc = ax.scatter(x[has_eff], y[has_eff], c=eff[has_eff], cmap='RdBu_r',
                                vmin=-vmax, vmax=vmax, s=58, alpha=0.9,
                                edgecolors='black', linewidths=0.5)
                scatter_ref = sc

            # Row combination (e.g. ANODIC · BIPHASIC) goes in the title so every
            # panel is self-labelled; the y-axis label stays short.
            lines = []
            if r == 0:
                lines.append(tt)
            if row_cols:
                lines.append(_row_label(group, row_cols))
            lines.append(f"n={len(x)} {point_noun}s")
            ax.set_title("\n".join(lines), fontsize=10)
            if xlim:
                ax.set_xlim(xlim)
            if ylim:
                ax.set_ylim(ylim)
            if r == nrows - 1:
                ax.set_xlabel(x_label, fontsize=9)
            if c == 0:
                ax.set_ylabel(y_label, fontsize=10)
            ax.grid(True, alpha=0.3)

    if scatter_ref is not None:
        cbar = fig.colorbar(scatter_ref, ax=axes.ravel().tolist(), shrink=0.6, pad=0.02)
        cbar.set_label('estim effect (ON − OFF %)  — red = positive, blue = negative',
                       fontsize=10)

    fig.suptitle(f"{title} — one point per {point_noun} (colour = estim effect"
                 f"{'; rows = ' + ' × '.join(row_cols) if row_cols else ''})",
                 fontsize=14, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved plot to {output_path}")
    plt.show()
    return fig


def run_half_distance_vs_current(trial_types=None, *, start_session_id=None,
                                 exclude_session_ids=None,
                                 effect_metric=COMPARISON_METRIC,
                                 base_required_conditions=None,
                                 exclude_other_estim=True,
                                 min_on_trials=COMPARISON_MIN_ON_TRIALS,
                                 far_fraction=DEFAULT_FAR_FRACTION,
                                 near_bins=DEFAULT_NEAR_BINS,
                                 bin_agg=DEFAULT_BIN_AGG, smoothing=DEFAULT_SMOOTHING,
                                 aggregate_by='spec', by_polarity=True, save_dir=None):
    """Build the half-distance table and draw the grid (cols = trial types; rows =
    anodic/cathodic when by_polarity). bin_agg ('median'/'mean') and smoothing
    ('isotonic'/'none') control the noise-robustness of the half-distance estimate.
    Returns (df, points_df)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] CORR HALF-DISTANCE vs CURRENT  trial_types={trial_types}  "
          f"effect_metric={effect_metric}  far_fraction={far_fraction}  "
          f"near_bins={near_bins}  bin_agg={bin_agg}  smoothing={smoothing}  "
          f"min_on={min_on_trials}  point={aggregate_by}  by_polarity={by_polarity}")

    df = build_current_spread_halfdist_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions,
        exclude_other_estim=exclude_other_estim, min_on_trials=min_on_trials,
        far_fraction=far_fraction, near_bins=near_bins,
        bin_agg=bin_agg, smoothing=smoothing)
    if len(df) == 0:
        print("Nothing to plot.")
        return df, pd.DataFrame()

    points = build_points(df, [HALFDIST_COL], aggregate_by)
    out_path = (os.path.join(save_dir, f"corr_half_distance_vs_{_slug(X_COLUMN)}.png")
                if save_dir else None)
    plot_metric_vs_current_by_trialtype(
        points, HALFDIST_COL,
        y_label='corr half-distance (µm)',
        title='How far high correlation spreads vs current spread',
        trial_types=trial_types, by_polarity=by_polarity,
        point_noun=aggregate_by, output_path=out_path)
    return df, points


def main_half_distance():
    """Y = correlation half-distance (how far high correlation reaches, µm),
    X = current spread, colour = effect; all trial types as subplots. Uses the
    shared COMPARISON_* config."""
    run_half_distance_vs_current(
        trial_types=(COMPARISON_TRIAL_TYPES or None),  # None/[] -> auto-discover
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        exclude_other_estim=True,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        aggregate_by='spec',   # one point per estim spec/condition
        save_dir=COMPARISON_SAVE_DIR,
    )


# ---------------------------------------------------------------------------
# Gaussian-smoothed effect heatmaps
#
# The scatter plots colour each point by its effect; here we convolve a Gaussian
# with those points to get a smooth field of the LOCAL MEAN effect over the plane,
# so the overall structure — where positive vs negative vs weak effects sit —
# reads at a glance. At each grid cell the field is the effect-weighted average of
# nearby points (Nadaraya–Watson kernel regression); cells with little data nearby
# are masked (shown gray) so empty regions don't get coloured. The heatmaps mirror
# the scatter facets (trial type × polarity), so each smoothed panel is the
# companion of the corresponding scatter panel.
# ---------------------------------------------------------------------------

DEFAULT_HEATMAP_GRID = 90            # grid cells per axis
DEFAULT_HEATMAP_BW = 0.3             # Gaussian bandwidth in per-axis-std units
DEFAULT_HEATMAP_DENSITY_FLOOR = 0.03  # mask cells below this fraction of peak density
DEFAULT_HEATMAP_MODE = 'mean'        # 'mean' = local weighted mean effect;
                                     # 'sum'  = raw summed effect splat (density-like)


def _gaussian_effect_field(x, y, eff, *, gridsize=DEFAULT_HEATMAP_GRID,
                           bandwidth=DEFAULT_HEATMAP_BW, mode=DEFAULT_HEATMAP_MODE,
                           density_floor=DEFAULT_HEATMAP_DENSITY_FLOOR, pad_frac=0.05,
                           xrange=None, yrange=None):
    """Convolve a Gaussian with each (x, y) point carrying value `eff` and evaluate
    on a grid. Axes are standardised (per-axis std) before weighting so the kernel
    isn't dominated by whichever axis has the larger raw units.

    xrange / yrange (lo, hi), when given, fix the evaluated grid extent so every
    panel shares one coordinate frame (else the data range ± pad is used).

    mode='mean' -> field[cell] = sum_i w_i eff_i / sum_i w_i (local mean effect,
    same units as effect); 'sum' -> field[cell] = sum_i w_i eff_i (unnormalised
    splat). Cells whose summed weight is < density_floor of the peak are set NaN
    (masked). Returns (gx, gy, field, density) or None if < 3 finite points."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    eff = np.asarray(eff, dtype=float)
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(eff)
    x, y, eff = x[m], y[m], eff[m]
    if len(x) < 3:
        return None
    sx = float(np.std(x)) or 1.0
    sy = float(np.std(y)) or 1.0
    xmin, xmax = float(x.min()), float(x.max())
    ymin, ymax = float(y.min()), float(y.max())
    px = pad_frac * ((xmax - xmin) or 1.0)
    py = pad_frac * ((ymax - ymin) or 1.0)
    if xrange is not None:
        gx = np.linspace(xrange[0], xrange[1], gridsize)
    else:
        gx = np.linspace(xmin - px, xmax + px, gridsize)
    if yrange is not None:
        gy = np.linspace(yrange[0], yrange[1], gridsize)
    else:
        gy = np.linspace(ymin - py, ymax + py, gridsize)
    GX, GY = np.meshgrid(gx, gy)
    dx = (GX[..., None] - x[None, None, :]) / sx
    dy = (GY[..., None] - y[None, None, :]) / sy
    W = np.exp(-0.5 * (dx * dx + dy * dy) / (bandwidth ** 2))
    density = W.sum(axis=-1)
    num = (W * eff[None, None, :]).sum(axis=-1)
    if mode == 'sum':
        field = num
    else:
        field = np.divide(num, density, out=np.full_like(num, np.nan),
                          where=density > 0)
    dmax = float(density.max()) or 1.0
    field = np.where(density / dmax >= density_floor, field, np.nan)
    return gx, gy, field, density


def _draw_effect_heatmap(ax, sub, y_col, *, vmax, bandwidth=DEFAULT_HEATMAP_BW,
                         gridsize=DEFAULT_HEATMAP_GRID, mode=DEFAULT_HEATMAP_MODE,
                         density_floor=DEFAULT_HEATMAP_DENSITY_FLOOR,
                         show_points=True, xrange=None, yrange=None, x_col=X_COLUMN):
    """Draw one smoothed effect heatmap panel. Returns the pcolormesh (for the
    shared colorbar) or None if too few points. xrange/yrange fix the grid extent
    and axis limits so panels are comparable."""
    d = sub[[x_col, y_col, 'effect_size']].dropna()
    ax.set_facecolor('#ededed')  # masked/no-data cells show through as gray

    def _apply_lims():
        if xrange is not None:
            ax.set_xlim(xrange)
        if yrange is not None:
            ax.set_ylim(yrange)

    if len(d) < 3:
        ax.text(0.5, 0.5, f"n={len(d)} (too few)", ha='center', va='center',
                transform=ax.transAxes, fontsize=9, color='gray')
        _apply_lims()
        return None
    res = _gaussian_effect_field(
        d[x_col].to_numpy(), d[y_col].to_numpy(), d['effect_size'].to_numpy(),
        gridsize=gridsize, bandwidth=bandwidth, mode=mode, density_floor=density_floor,
        xrange=xrange, yrange=yrange)
    if res is None:
        _apply_lims()
        return None
    gx, gy, field, _ = res
    mesh = ax.pcolormesh(gx, gy, np.ma.masked_invalid(field), cmap='RdBu_r',
                         vmin=-vmax, vmax=vmax, shading='auto')
    if show_points:
        ax.scatter(d[x_col], d[y_col], s=9, c='black', alpha=0.35, linewidths=0)
    _apply_lims()
    return mesh


def _effect_vmax(points, *, floor=1e-6):
    """Symmetric colour limit for the effect: max |effect_size| over the points."""
    eff = pd.to_numeric(points.get('effect_size'), errors='coerce')
    eff = eff[np.isfinite(eff)] if eff is not None else pd.Series([], dtype=float)
    return max(float(np.abs(eff).max()), floor) if len(eff) else 1.0


def plot_effect_heatmap_by_trialtype(points, y_col, *, y_label, title, trial_types,
                                     by_polarity=True, by_waveform=False,
                                     mode=DEFAULT_HEATMAP_MODE,
                                     bandwidth=DEFAULT_HEATMAP_BW,
                                     gridsize=DEFAULT_HEATMAP_GRID,
                                     density_floor=DEFAULT_HEATMAP_DENSITY_FLOOR,
                                     show_points=True, point_noun='spec',
                                     x_col=X_COLUMN, x_label=X_LABEL, output_path=None):
    """Smoothed-effect heatmap version of plot_metric_vs_current_by_trialtype:
    columns = trial types, rows = every present combination of polarity (by_polarity)
    × waveform (by_waveform). Each panel is the Gaussian-smoothed local-mean effect
    over (x_col, y_col)."""
    tts = [tt for tt in trial_types if (points['trial_type'] == tt).any()]
    if not tts:
        print("No trial types with points to plot.")
        return None
    row_cols = _resolve_row_cols(points, by_polarity, by_waveform)
    groups, row_cols = _row_groups(points, row_cols)
    ncols, nrows = len(tts), len(groups)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 4.4 * nrows),
                             squeeze=False, constrained_layout=True)
    vmax = _effect_vmax(points)
    # Shared grid extent + axis limits across every panel.
    xrange = _axis_limits(points[x_col])
    yrange = _axis_limits(points[y_col])

    mesh_ref = None
    for r, group in enumerate(groups):
        for c, tt in enumerate(tts):
            ax = axes[r][c]
            sub = _filter_rows(points[points['trial_type'] == tt], group)
            mesh = _draw_effect_heatmap(
                ax, sub, y_col, vmax=vmax, bandwidth=bandwidth, gridsize=gridsize,
                mode=mode, density_floor=density_floor, show_points=show_points,
                xrange=xrange, yrange=yrange, x_col=x_col)
            if mesh is not None:
                mesh_ref = mesh
            lines = []
            if r == 0:
                lines.append(tt)
            if row_cols:
                lines.append(_row_label(group, row_cols))
            n_here = int(sub[[x_col, y_col, 'effect_size']].dropna().shape[0])
            lines.append(f"n={n_here} {point_noun}s")
            ax.set_title("\n".join(lines), fontsize=10)
            if r == nrows - 1:
                ax.set_xlabel(x_label, fontsize=9)
            if c == 0:
                ax.set_ylabel(y_label, fontsize=10)

    if mesh_ref is not None:
        cbar = fig.colorbar(mesh_ref, ax=axes.ravel().tolist(), shrink=0.6, pad=0.02)
        lbl = ('local mean estim effect (ON − OFF %)' if mode == 'mean'
               else 'summed effect (splat)')
        cbar.set_label(f"{lbl}  — red = positive, blue = negative", fontsize=10)

    fig.suptitle(f"{title} — Gaussian-smoothed effect field"
                 f"{'; rows = ' + ' × '.join(row_cols) if row_cols else ''}",
                 fontsize=14, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved effect heatmap to {output_path}")
    plt.show()
    return fig


def plot_effect_heatmap_grid(pts, *, scales, threshold, trial_type='',
                             point_noun='spec', mode=DEFAULT_HEATMAP_MODE,
                             bandwidth=DEFAULT_HEATMAP_BW,
                             gridsize=DEFAULT_HEATMAP_GRID,
                             density_floor=DEFAULT_HEATMAP_DENSITY_FLOOR,
                             show_points=True, xrange=None, ylim_by_family=None,
                             vmax=None, output_path=None):
    """Smoothed-effect heatmap version of the tuning grid (rows = mean/max/area,
    cols = probe scale) for one already-filtered subset (e.g. one trial_type ×
    polarity). Each panel smooths the effect over (current_per_second, metric).
    xrange / ylim_by_family / vmax fix the shared frame across separate figures;
    if None they are computed from this subset."""
    scale_items = sorted(scales.items(), key=lambda kv: kv[1])
    nrows, ncols = len(FAMILIES), len(scale_items)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.6 * ncols, 4.0 * nrows),
                             squeeze=False, constrained_layout=True)
    if vmax is None:
        vmax = _effect_vmax(pts)
    if xrange is None:
        xrange = _axis_limits(pts[X_COLUMN]) if X_COLUMN in pts.columns else None
    if ylim_by_family is None:
        ylim_by_family = _family_ylims(pts, scales)

    mesh_ref = None
    for r, family in enumerate(FAMILIES):
        for c, (scale_label, n) in enumerate(scale_items):
            ax = axes[r][c]
            mesh = _draw_effect_heatmap(
                ax, pts, _metric_col(family, n), vmax=vmax, bandwidth=bandwidth,
                gridsize=gridsize, mode=mode, density_floor=density_floor,
                show_points=show_points, xrange=xrange,
                yrange=(ylim_by_family or {}).get(family))
            if mesh is not None:
                mesh_ref = mesh
            if r == 0:
                ax.set_title(scale_label, fontsize=10)
            if r == nrows - 1:
                ax.set_xlabel(X_LABEL, fontsize=9)
            if c == 0:
                ylab = FAMILY_LABELS[family]
                if family == FAMILY_AREA:
                    ylab += f" (ρ>{threshold:g})"
                ax.set_ylabel(ylab, fontsize=10)

    if mesh_ref is not None:
        cbar = fig.colorbar(mesh_ref, ax=axes.ravel().tolist(), shrink=0.6, pad=0.02)
        lbl = ('local mean estim effect (ON − OFF %)' if mode == 'mean'
               else 'summed effect (splat)')
        cbar.set_label(f"{lbl}  — red = positive, blue = negative", fontsize=10)

    fig.suptitle(f"Effect structure over current spread × tuning — smoothed field"
                 f"{('  [' + str(trial_type) + ']') if trial_type else ''}",
                 fontsize=13, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved effect heatmap grid to {output_path}")
    plt.show()
    return fig


def run_half_distance_effect_heatmap(trial_types=None, *, start_session_id=None,
                                     exclude_session_ids=None,
                                     effect_metric=COMPARISON_METRIC,
                                     base_required_conditions=None,
                                     exclude_other_estim=True,
                                     min_on_trials=COMPARISON_MIN_ON_TRIALS,
                                     far_fraction=DEFAULT_FAR_FRACTION,
                                     near_bins=DEFAULT_NEAR_BINS,
                                     bin_agg=DEFAULT_BIN_AGG, smoothing=DEFAULT_SMOOTHING,
                                     aggregate_by='spec', by_polarity=True,
                                     mode=DEFAULT_HEATMAP_MODE, bandwidth=DEFAULT_HEATMAP_BW,
                                     save_dir=None):
    """Gaussian-smoothed effect heatmap over (current spread, correlation
    half-distance), faceted by trial type × polarity. Returns (df, points_df)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    df = build_current_spread_halfdist_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions,
        exclude_other_estim=exclude_other_estim, min_on_trials=min_on_trials,
        far_fraction=far_fraction, near_bins=near_bins,
        bin_agg=bin_agg, smoothing=smoothing)
    if len(df) == 0:
        print("Nothing to plot.")
        return df, pd.DataFrame()
    points = build_points(df, [HALFDIST_COL], aggregate_by)
    out_path = (os.path.join(save_dir, f"corr_half_distance_heatmap_vs_{_slug(X_COLUMN)}.png")
                if save_dir else None)
    plot_effect_heatmap_by_trialtype(
        points, HALFDIST_COL, y_label='corr half-distance (µm)',
        title='Effect structure: current spread × correlation spread',
        trial_types=trial_types, by_polarity=by_polarity, mode=mode,
        bandwidth=bandwidth, point_noun=aggregate_by, output_path=out_path)
    return df, points


def run_tuning_effect_heatmap(trial_types=None, *, start_session_id=None,
                              exclude_session_ids=None,
                              effect_metric=COMPARISON_METRIC,
                              base_required_conditions=None,
                              scales=DEFAULT_SCALES, threshold=DEFAULT_HIGH_CORR_THRESHOLD,
                              exclude_other_estim=True,
                              min_on_trials=COMPARISON_MIN_ON_TRIALS,
                              aggregate_by='spec', by_polarity=True,
                              mode=DEFAULT_HEATMAP_MODE, bandwidth=DEFAULT_HEATMAP_BW,
                              save_dir=None):
    """Gaussian-smoothed effect heatmap version of the tuning grid, one figure per
    (trial_type, polarity). Returns (per_spec_df, points_df)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    df, metric_cols = build_current_spread_tuning_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions, scales=scales,
        threshold=threshold, exclude_other_estim=exclude_other_estim,
        min_on_trials=min_on_trials)
    if len(df) == 0:
        print("Nothing to plot.")
        return df, pd.DataFrame()
    points = build_points(df, metric_cols, aggregate_by)
    # Shared frame across every (trial_type, polarity) figure.
    xrange = _axis_limits(points[X_COLUMN])
    ylim_by_family = _family_ylims(points, scales)
    vmax = _effect_vmax(points)
    polarities = (_present_polarities(points)
                  if (by_polarity and points['polarity'].notna().any()) else [None])
    for tt in trial_types:
        for pol in polarities:
            pts_tt = points[points['trial_type'] == tt]
            if pol is not None:
                pts_tt = pts_tt[pts_tt['polarity'] == pol]
            if len(pts_tt) == 0:
                continue
            tag = tt + (f"  [{_pol_short(pol)}]" if pol is not None else "")
            fname = f"tuning_heatmap_vs_{_slug(X_COLUMN)}_{_slug(tt)}" + \
                    (f"_{_pol_short(pol)}" if pol is not None else "") + ".png"
            out_path = os.path.join(save_dir, fname) if save_dir else None
            plot_effect_heatmap_grid(
                pts_tt, scales=scales, threshold=threshold, trial_type=tag,
                point_noun=aggregate_by, mode=mode, bandwidth=bandwidth,
                xrange=xrange, ylim_by_family=ylim_by_family, vmax=vmax,
                output_path=out_path)
    return df, points


def main_half_distance_heatmap():
    """Gaussian-smoothed effect heatmap over current spread × correlation
    half-distance (companion to main_half_distance). Uses the COMPARISON_* config."""
    run_half_distance_effect_heatmap(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        exclude_other_estim=True,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        aggregate_by='spec',
        save_dir=COMPARISON_SAVE_DIR,
    )


def main_tuning_heatmap():
    """Gaussian-smoothed effect heatmap version of the tuning grid (companion to
    main). Uses the COMPARISON_* config."""
    run_tuning_effect_heatmap(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        scales=DEFAULT_SCALES,
        threshold=DEFAULT_HIGH_CORR_THRESHOLD,
        exclude_other_estim=True,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        aggregate_by='spec',
        save_dir=COMPARISON_SAVE_DIR,
    )


# ---------------------------------------------------------------------------
# Tuning-region symmetry: is the estim locus CENTERED in a correlated region?
#
# On the linear probe each non-estim channel c sits at a signed distance d = y_c −
# y0 from the estim locus (y0 = mean probe position of the spec's active channels)
# and has a correlation rho to that locus. If the correlated tissue is centred on
# the locus, the correlation "mass" is balanced above/below (offset ≈ 0); if the
# locus sits at the edge of a patch, the mass is skewed to one side.
#
# Metric = correlation-weighted CENTROID OFFSET, soft-scaled by the spec's own
# correlation half-distance and corrected for probe geometry:
#     w_c = max(rho_c, 0) · exp(−½ (d / λ)²),   λ = corr half-distance
#     offset_obs  = Σ w_c d_c / Σ w_c
#     offset_geom = Σ g_c d_c / Σ g_c           (g_c = the Gaussian alone)
#     offset      = offset_obs − offset_geom    (µm; 0 = centred)
# Subtracting offset_geom removes the skew that comes purely from the probe edge
# truncating one side (a channel near the tip has no neighbours above it), so what
# remains is tuning-driven asymmetry. Positive = correlated mass skewed toward
# increasing probe-y. Undefined (None) when half-distance is undefined or one side
# has no correlated channels within the window.
# ---------------------------------------------------------------------------

SYM_COL = 'corr_sym_offset_um'
DEFAULT_SYM_GEOMETRY_CORRECT = True   # subtract the probe-geometry baseline skew
DEFAULT_SYM_MIN_SIDE = 1              # min contributing channels required per side


def _symmetry_offset_for_spec(corr_metric, estim_channels, channels_with_data, coords,
                              half_distance, *, exclude_other_estim=True,
                              geometry_correct=DEFAULT_SYM_GEOMETRY_CORRECT,
                              min_side_channels=DEFAULT_SYM_MIN_SIDE):
    """Geometry-corrected, Gaussian-weighted correlation-centroid offset (µm) of the
    correlated region about the estim locus, or None if undefined."""
    if half_distance is None or half_distance <= 0:
        return None
    est_present = [e for e in estim_channels if e in channels_with_data]
    if not est_present:
        return None
    y0 = float(np.mean([coords[e][1] for e in est_present]))
    exclude = set(estim_channels) if exclude_other_estim else set()
    est_set = set(est_present)
    lam = float(half_distance)

    ds, ws, gs = [], [], []
    up = down = 0
    for c in channels_with_data:
        if c in exclude or c in est_set:
            continue
        rhos = [corr_metric.pair_similarity(channel_to_str(e), channel_to_str(c))
                for e in est_present]
        rhos = [r for r in rhos if r is not None and np.isfinite(r)]
        if not rhos:
            continue
        rho = float(np.mean(rhos))
        d = float(coords[c][1]) - y0
        g = float(np.exp(-0.5 * (d / lam) ** 2))
        ds.append(d)
        gs.append(g)
        ws.append(max(rho, 0.0) * g)
        if d > 0:
            up += 1
        elif d < 0:
            down += 1
    if up < min_side_channels or down < min_side_channels:
        return None
    ds = np.asarray(ds)
    ws = np.asarray(ws)
    gs = np.asarray(gs)
    if ws.sum() <= 0:
        return None
    offset = float((ws * ds).sum() / ws.sum())
    if geometry_correct and gs.sum() > 0:
        offset -= float((gs * ds).sum() / gs.sum())
    return offset


def compute_session_symmetry(session_id, *, exclude_other_estim=True,
                             far_fraction=DEFAULT_FAR_FRACTION,
                             near_bins=DEFAULT_NEAR_BINS, bin_agg=DEFAULT_BIN_AGG,
                             smoothing=DEFAULT_SMOOTHING,
                             geometry_correct=DEFAULT_SYM_GEOMETRY_CORRECT,
                             min_side_channels=DEFAULT_SYM_MIN_SIDE):
    """{estim_spec_id: {HALFDIST_COL, SYM_COL}} for one session. The half-distance
    sets the Gaussian scale λ for the symmetry offset, so both are computed here."""
    metrics, channels_with_data, coords = prepare_session_metrics(session_id)
    if metrics is None:
        return {}
    corr_metric = next((m for m in metrics if m.name == CORR_METRIC_NAME), None)
    if corr_metric is None:
        print(f"  {session_id}: no '{CORR_METRIC_NAME}' metric available; skipping")
        return {}
    pitch = _probe_pitch(coords)
    estim_by_spec = fetch_active_estim_channels_by_spec(session_id)
    out = {}
    for spec_id, estim_channels in estim_by_spec.items():
        hd = _half_distance_for_spec(
            corr_metric, estim_channels, channels_with_data, coords,
            exclude_other_estim=exclude_other_estim, pitch=pitch,
            far_fraction=far_fraction, near_bins=near_bins,
            bin_agg=bin_agg, smoothing=smoothing)
        sym = _symmetry_offset_for_spec(
            corr_metric, estim_channels, channels_with_data, coords, hd,
            exclude_other_estim=exclude_other_estim,
            geometry_correct=geometry_correct, min_side_channels=min_side_channels)
        out[int(spec_id)] = {HALFDIST_COL: hd, SYM_COL: sym}
    return out


def build_current_spread_symmetry_table(trial_types, *, start_session_id=None,
                                        exclude_session_ids=None,
                                        effect_metric=COMPARISON_METRIC,
                                        base_required_conditions=None,
                                        exclude_other_estim=True,
                                        min_on_trials=COMPARISON_MIN_ON_TRIALS,
                                        far_fraction=DEFAULT_FAR_FRACTION,
                                        near_bins=DEFAULT_NEAR_BINS,
                                        bin_agg=DEFAULT_BIN_AGG,
                                        smoothing=DEFAULT_SMOOTHING,
                                        geometry_correct=DEFAULT_SYM_GEOMETRY_CORRECT,
                                        min_side_channels=DEFAULT_SYM_MIN_SIDE):
    """Per-(session, estim_spec, trial_type) table with current, effect, the corr
    half-distance, and the symmetry offset. Returns the DataFrame."""
    frames = []
    for tt in trial_types:
        rc = _rc_for_trial_type(base_required_conditions, tt)
        print(f"\n--- current/spec membership for trial_type={tt!r} ---")
        df_tt = _effect_and_current_table(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=effect_metric, required_conditions=rc)
        if len(df_tt) == 0:
            print(f"  (no specs for trial_type={tt!r})")
            continue
        df_tt = df_tt[df_tt['n_on'] >= min_on_trials].copy()
        df_tt['trial_type'] = tt
        frames.append(df_tt)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    _attach_estim_metrics(df)

    by_session = {}
    for sid in sorted(df['session_id'].unique().tolist()):
        print(f"\n=== tuning-region symmetry for session {sid} ===")
        by_session[sid] = compute_session_symmetry(
            sid, exclude_other_estim=exclude_other_estim, far_fraction=far_fraction,
            near_bins=near_bins, bin_agg=bin_agg, smoothing=smoothing,
            geometry_correct=geometry_correct, min_side_channels=min_side_channels)

    for col in (HALFDIST_COL, SYM_COL):
        df[col] = [
            (by_session.get(s, {}).get(int(spec), {}) or {}).get(col)
            for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    n_scored = df[SYM_COL].notna().sum()
    print(f"\nBuilt symmetry table: {len(df)} specs across "
          f"{df['session_id'].nunique()} sessions; {n_scored} have a symmetry offset")
    return df


def run_symmetry_vs_current(trial_types=None, *, start_session_id=None,
                            exclude_session_ids=None, effect_metric=COMPARISON_METRIC,
                            base_required_conditions=None, exclude_other_estim=True,
                            min_on_trials=COMPARISON_MIN_ON_TRIALS,
                            aggregate_by='spec', by_polarity=True,
                            heatmap=False, mode=DEFAULT_HEATMAP_MODE,
                            bandwidth=DEFAULT_HEATMAP_BW, save_dir=None):
    """Tuning-region symmetry offset vs current, faceted by trial type × polarity.
    heatmap=False draws the effect-coloured scatter; True draws the Gaussian-smoothed
    effect field. Returns (df, points_df)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] TUNING SYMMETRY vs CURRENT  trial_types={trial_types}  "
          f"effect_metric={effect_metric}  min_on={min_on_trials}  point={aggregate_by}  "
          f"by_polarity={by_polarity}  heatmap={heatmap}")
    df = build_current_spread_symmetry_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions,
        exclude_other_estim=exclude_other_estim, min_on_trials=min_on_trials)
    if len(df) == 0:
        print("Nothing to plot.")
        return df, pd.DataFrame()
    points = build_points(df, [SYM_COL, HALFDIST_COL], aggregate_by)
    y_label = 'corr symmetry offset (µm)  — 0 = centred'
    title = 'Tuning-region symmetry (centroid offset) vs current'
    kind = 'heatmap' if heatmap else 'scatter'
    out_path = (os.path.join(save_dir, f"tuning_symmetry_{kind}_vs_{_slug(X_COLUMN)}.png")
                if save_dir else None)
    if heatmap:
        plot_effect_heatmap_by_trialtype(
            points, SYM_COL, y_label=y_label, title=title, trial_types=trial_types,
            by_polarity=by_polarity, mode=mode, bandwidth=bandwidth,
            point_noun=aggregate_by, output_path=out_path)
    else:
        plot_metric_vs_current_by_trialtype(
            points, SYM_COL, y_label=y_label, title=title, trial_types=trial_types,
            by_polarity=by_polarity, point_noun=aggregate_by, output_path=out_path)
    return df, points


def main_symmetry():
    """Tuning-region symmetry offset vs current (effect-coloured scatter), faceted
    by trial type × polarity. Uses the shared COMPARISON_* config."""
    run_symmetry_vs_current(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        exclude_other_estim=True,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        aggregate_by='spec',
        heatmap=False,
        save_dir=COMPARISON_SAVE_DIR,
    )


def main_symmetry_heatmap():
    """Gaussian-smoothed effect field over current × tuning-region symmetry offset.
    Uses the shared COMPARISON_* config."""
    run_symmetry_vs_current(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        exclude_other_estim=True,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        aggregate_by='spec',
        heatmap=True,
        save_dir=COMPARISON_SAVE_DIR,
    )


# ---------------------------------------------------------------------------
# Correlation strength WITHIN the half-distance: how high is the correlation in
# the region we call "correlated"?
#
# Half-distance says how FAR correlation reaches; this says how STRONG it is
# inside that reach. For each spec we take the (median) rho over channels within
# its own corr half-distance radius of the estim site. A region can be
# wide-but-weak or narrow-but-strong, so this disentangles the two.
# ---------------------------------------------------------------------------

CORRINHALF_COL = 'corr_in_half_distance'


def _mean_corr_within_for_spec(corr_metric, estim_channels, channels_with_data,
                               coords, radius, *, exclude_other_estim=True,
                               agg=DEFAULT_BIN_AGG):
    """(median/mean) rho over channels within `radius` µm of the spec's estim
    channels, or None. `radius` is the spec's corr half-distance."""
    if radius is None or radius <= 0:
        return None
    est_present = [e for e in estim_channels if e in channels_with_data]
    if not est_present:
        return None
    exclude = set(estim_channels) if exclude_other_estim else set()
    est_set = set(est_present)
    vals = []
    for e in est_present:
        e_str = channel_to_str(e)
        e_xy = coords[e]
        for c in channels_with_data:
            if c in exclude or c in est_set:
                continue
            if float(np.linalg.norm(coords[c] - e_xy)) > radius:
                continue
            r = corr_metric.pair_similarity(e_str, channel_to_str(c))
            if r is not None and np.isfinite(r):
                vals.append(float(r))
    if not vals:
        return None
    return float(np.median(vals) if agg == 'median' else np.mean(vals))


def compute_session_corr_in_half_distance(session_id, *, exclude_other_estim=True,
                                          far_fraction=DEFAULT_FAR_FRACTION,
                                          near_bins=DEFAULT_NEAR_BINS,
                                          bin_agg=DEFAULT_BIN_AGG,
                                          smoothing=DEFAULT_SMOOTHING):
    """{estim_spec_id: {HALFDIST_COL, CORRINHALF_COL}} for one session. The
    half-distance sets the radius, so both are computed in one pass."""
    metrics, channels_with_data, coords = prepare_session_metrics(session_id)
    if metrics is None:
        return {}
    corr_metric = next((m for m in metrics if m.name == CORR_METRIC_NAME), None)
    if corr_metric is None:
        print(f"  {session_id}: no '{CORR_METRIC_NAME}' metric available; skipping")
        return {}
    pitch = _probe_pitch(coords)
    estim_by_spec = fetch_active_estim_channels_by_spec(session_id)
    out = {}
    for spec_id, estim_channels in estim_by_spec.items():
        hd = _half_distance_for_spec(
            corr_metric, estim_channels, channels_with_data, coords,
            exclude_other_estim=exclude_other_estim, pitch=pitch,
            far_fraction=far_fraction, near_bins=near_bins,
            bin_agg=bin_agg, smoothing=smoothing)
        ch = _mean_corr_within_for_spec(
            corr_metric, estim_channels, channels_with_data, coords, hd,
            exclude_other_estim=exclude_other_estim, agg=bin_agg)
        out[int(spec_id)] = {HALFDIST_COL: hd, CORRINHALF_COL: ch}
    return out


def build_current_spread_corrinhalf_table(trial_types, *, start_session_id=None,
                                          exclude_session_ids=None,
                                          effect_metric=COMPARISON_METRIC,
                                          base_required_conditions=None,
                                          exclude_other_estim=True,
                                          min_on_trials=COMPARISON_MIN_ON_TRIALS,
                                          far_fraction=DEFAULT_FAR_FRACTION,
                                          near_bins=DEFAULT_NEAR_BINS,
                                          bin_agg=DEFAULT_BIN_AGG,
                                          smoothing=DEFAULT_SMOOTHING):
    """Per-(session, estim_spec, trial_type) table with current, effect, the corr
    half-distance, and the correlation strength within it. Returns the DataFrame."""
    frames = []
    for tt in trial_types:
        rc = _rc_for_trial_type(base_required_conditions, tt)
        print(f"\n--- current/spec membership for trial_type={tt!r} ---")
        df_tt = _effect_and_current_table(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=effect_metric, required_conditions=rc)
        if len(df_tt) == 0:
            print(f"  (no specs for trial_type={tt!r})")
            continue
        df_tt = df_tt[df_tt['n_on'] >= min_on_trials].copy()
        df_tt['trial_type'] = tt
        frames.append(df_tt)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    _attach_estim_metrics(df)

    by_session = {}
    for sid in sorted(df['session_id'].unique().tolist()):
        print(f"\n=== corr-within-half-distance for session {sid} ===")
        by_session[sid] = compute_session_corr_in_half_distance(
            sid, exclude_other_estim=exclude_other_estim, far_fraction=far_fraction,
            near_bins=near_bins, bin_agg=bin_agg, smoothing=smoothing)

    for col in (HALFDIST_COL, CORRINHALF_COL):
        df[col] = [
            (by_session.get(s, {}).get(int(spec), {}) or {}).get(col)
            for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    n_scored = df[CORRINHALF_COL].notna().sum()
    print(f"\nBuilt corr-in-half-distance table: {len(df)} specs across "
          f"{df['session_id'].nunique()} sessions; {n_scored} scored")
    return df


def run_corr_in_half_distance(trial_types=None, *, start_session_id=None,
                              exclude_session_ids=None, effect_metric=COMPARISON_METRIC,
                              base_required_conditions=None, exclude_other_estim=True,
                              min_on_trials=COMPARISON_MIN_ON_TRIALS,
                              aggregate_by='spec', by_polarity=True,
                              heatmap=False, mode=DEFAULT_HEATMAP_MODE,
                              bandwidth=DEFAULT_HEATMAP_BW, save_dir=None):
    """Correlation strength within the half-distance vs current, faceted by trial
    type × polarity. heatmap=False -> effect-coloured scatter; True -> smoothed
    effect field. Returns (df, points_df)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] CORR-IN-HALF-DISTANCE vs CURRENT  trial_types={trial_types}  "
          f"effect_metric={effect_metric}  min_on={min_on_trials}  point={aggregate_by}  "
          f"by_polarity={by_polarity}  heatmap={heatmap}")
    df = build_current_spread_corrinhalf_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions,
        exclude_other_estim=exclude_other_estim, min_on_trials=min_on_trials)
    if len(df) == 0:
        print("Nothing to plot.")
        return df, pd.DataFrame()
    points = build_points(df, [CORRINHALF_COL, HALFDIST_COL], aggregate_by)
    y_label = 'mean corr within half-distance'
    title = 'Correlation strength within its half-distance vs current'
    kind = 'heatmap' if heatmap else 'scatter'
    out_path = (os.path.join(save_dir, f"corr_in_halfdist_{kind}_vs_{_slug(X_COLUMN)}.png")
                if save_dir else None)
    if heatmap:
        plot_effect_heatmap_by_trialtype(
            points, CORRINHALF_COL, y_label=y_label, title=title,
            trial_types=trial_types, by_polarity=by_polarity, mode=mode,
            bandwidth=bandwidth, point_noun=aggregate_by, output_path=out_path)
    else:
        plot_metric_vs_current_by_trialtype(
            points, CORRINHALF_COL, y_label=y_label, title=title,
            trial_types=trial_types, by_polarity=by_polarity,
            point_noun=aggregate_by, output_path=out_path)
    return df, points


def main_corr_in_half_distance():
    """Correlation strength within its half-distance vs current (effect-coloured
    scatter). Uses the shared COMPARISON_* config."""
    run_corr_in_half_distance(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        exclude_other_estim=True, min_on_trials=COMPARISON_MIN_ON_TRIALS,
        aggregate_by='spec', heatmap=False, save_dir=COMPARISON_SAVE_DIR,
    )


def main_corr_in_half_distance_heatmap():
    """Gaussian-smoothed effect field over current × correlation-within-half-distance.
    Uses the shared COMPARISON_* config."""
    run_corr_in_half_distance(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        exclude_other_estim=True, min_on_trials=COMPARISON_MIN_ON_TRIALS,
        aggregate_by='spec', heatmap=True, save_dir=COMPARISON_SAVE_DIR,
    )


# ===========================================================================
# Unified single-Y spec metrics — ONE place to choose the Y-axis metric(s).
#
# To plot a different Y metric: edit Y_METRIC_SELECTION below (or pass y_metrics=
# to run_spec_metrics). Every selected metric is built from one shared table and
# saved to its OWN file ("<key>_<scatter|heatmap>_vs_<xmetric>.png"), so listing
# several generates several figures in one run without overwriting.
# ===========================================================================

# key -> (dataframe column, y-axis label). Add a row to expose a new single-Y metric.
Y_METRICS = {
    'half_distance': (HALFDIST_COL, 'corr half-distance (µm)'),
    'corr_in_half': (CORRINHALF_COL, 'mean corr within half-distance'),
    'symmetry': (SYM_COL, 'corr symmetry offset (µm)  — 0 = centred'),
}
_Y_METRIC_TITLES = {
    'half_distance': 'How far high correlation spreads vs current',
    'corr_in_half': 'Correlation strength within its half-distance vs current',
    'symmetry': 'Tuning-region symmetry (centroid offset) vs current',
}
# Which Y metric(s) to plot. Each is saved to its own file.
Y_METRIC_SELECTION = ('half_distance', 'corr_in_half', 'symmetry')


def compute_session_spec_metrics(session_id, *, exclude_other_estim=True,
                                 far_fraction=DEFAULT_FAR_FRACTION,
                                 near_bins=DEFAULT_NEAR_BINS, bin_agg=DEFAULT_BIN_AGG,
                                 smoothing=DEFAULT_SMOOTHING,
                                 geometry_correct=DEFAULT_SYM_GEOMETRY_CORRECT,
                                 min_side_channels=DEFAULT_SYM_MIN_SIDE):
    """{estim_spec_id: {HALFDIST_COL, SYM_COL, CORRINHALF_COL}} for one session —
    every single-Y spec metric in one pass (they share the correlation matrix and
    the half-distance, so computing them together is far cheaper than separately)."""
    metrics, channels_with_data, coords = prepare_session_metrics(session_id)
    if metrics is None:
        return {}
    corr_metric = next((m for m in metrics if m.name == CORR_METRIC_NAME), None)
    if corr_metric is None:
        print(f"  {session_id}: no '{CORR_METRIC_NAME}' metric available; skipping")
        return {}
    pitch = _probe_pitch(coords)
    estim_by_spec = fetch_active_estim_channels_by_spec(session_id)
    out = {}
    for spec_id, estim_channels in estim_by_spec.items():
        hd = _half_distance_for_spec(
            corr_metric, estim_channels, channels_with_data, coords,
            exclude_other_estim=exclude_other_estim, pitch=pitch,
            far_fraction=far_fraction, near_bins=near_bins,
            bin_agg=bin_agg, smoothing=smoothing)
        sym = _symmetry_offset_for_spec(
            corr_metric, estim_channels, channels_with_data, coords, hd,
            exclude_other_estim=exclude_other_estim,
            geometry_correct=geometry_correct, min_side_channels=min_side_channels)
        cih = _mean_corr_within_for_spec(
            corr_metric, estim_channels, channels_with_data, coords, hd,
            exclude_other_estim=exclude_other_estim, agg=bin_agg)
        out[int(spec_id)] = {HALFDIST_COL: hd, SYM_COL: sym, CORRINHALF_COL: cih}
    return out


def build_spec_metric_table(trial_types, *, start_session_id=None,
                            exclude_session_ids=None, effect_metric=COMPARISON_METRIC,
                            base_required_conditions=None, exclude_other_estim=True,
                            min_on_trials=COMPARISON_MIN_ON_TRIALS):
    """Per-(session, estim_spec, trial_type) table with current, effect, and every
    single-Y spec metric (half-distance, symmetry, corr-in-half)."""
    frames = []
    for tt in trial_types:
        rc = _rc_for_trial_type(base_required_conditions, tt)
        print(f"\n--- current/spec membership for trial_type={tt!r} ---")
        df_tt = _effect_and_current_table(
            start_session_id=start_session_id, exclude_session_ids=exclude_session_ids,
            metric=effect_metric, required_conditions=rc)
        if len(df_tt) == 0:
            print(f"  (no specs for trial_type={tt!r})")
            continue
        df_tt = df_tt[df_tt['n_on'] >= min_on_trials].copy()
        df_tt['trial_type'] = tt
        frames.append(df_tt)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    _attach_estim_metrics(df)

    by_session = {}
    for sid in sorted(df['session_id'].unique().tolist()):
        print(f"\n=== spec metrics for session {sid} ===")
        by_session[sid] = compute_session_spec_metrics(
            sid, exclude_other_estim=exclude_other_estim)
    for col in (HALFDIST_COL, SYM_COL, CORRINHALF_COL):
        df[col] = [
            (by_session.get(s, {}).get(int(spec), {}) or {}).get(col)
            for s, spec in zip(df['session_id'], df['estim_spec_id'])]
    return df


def run_spec_metrics(trial_types=None, *, y_metrics=Y_METRIC_SELECTION,
                     x_metrics=(X_METRIC,), heatmap=False,
                     start_session_id=None, exclude_session_ids=None,
                     effect_metric=COMPARISON_METRIC, base_required_conditions=None,
                     exclude_other_estim=True, min_on_trials=COMPARISON_MIN_ON_TRIALS,
                     aggregate_by='spec', by_polarity=True, by_waveform=True,
                     mode=DEFAULT_HEATMAP_MODE, bandwidth=DEFAULT_HEATMAP_BW,
                     save_dir=None):
    """Build the spec-metric table ONCE, then plot every (x_metric, y_metric) combo
    to its own file — scatter, or smoothed effect heatmap when heatmap=True. Rows
    are every present combination of polarity (by_polarity) × waveform
    (by_waveform). x_metrics keys index X_LABELS (e.g. 'total_current_uA',
    'pulse_rate_hz')."""
    if isinstance(y_metrics, str):
        y_metrics = (y_metrics,)
    if isinstance(x_metrics, str):
        x_metrics = (x_metrics,)
    unknown = [k for k in y_metrics if k not in Y_METRICS]
    if unknown:
        raise ValueError(f"unknown y_metrics {unknown}; choose from {list(Y_METRICS)}")
    unknown_x = [k for k in x_metrics if k not in X_LABELS]
    if unknown_x:
        raise ValueError(f"unknown x_metrics {unknown_x}; choose from {list(X_LABELS)}")
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] SPEC METRICS  x_metrics={list(x_metrics)}  "
          f"y_metrics={list(y_metrics)}  heatmap={heatmap}  trial_types={trial_types}  "
          f"point={aggregate_by}  by_polarity={by_polarity}  by_waveform={by_waveform}")

    df = build_spec_metric_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions,
        exclude_other_estim=exclude_other_estim, min_on_trials=min_on_trials)
    if len(df) == 0:
        print("Nothing to plot.")
        return df, pd.DataFrame()

    cols = [Y_METRICS[k][0] for k in y_metrics]
    points = build_points(df, list(dict.fromkeys(cols + [HALFDIST_COL])), aggregate_by)
    kind = 'heatmap' if heatmap else 'scatter'
    for x_key in x_metrics:
        x_label = X_LABELS.get(x_key, x_key)
        for key in y_metrics:
            col, label = Y_METRICS[key]
            title = _Y_METRIC_TITLES.get(key, label)
            out_path = (os.path.join(save_dir, f"{key}_{kind}_vs_{_slug(x_key)}.png")
                        if save_dir else None)
            print(f"\n### y='{key}' vs x='{x_key}' ({kind}) ###")
            if heatmap:
                plot_effect_heatmap_by_trialtype(
                    points, col, y_label=label, title=title, trial_types=trial_types,
                    by_polarity=by_polarity, by_waveform=by_waveform, mode=mode,
                    bandwidth=bandwidth, point_noun=aggregate_by,
                    x_col=x_key, x_label=x_label, output_path=out_path)
            else:
                plot_metric_vs_current_by_trialtype(
                    points, col, y_label=label, title=title, trial_types=trial_types,
                    by_polarity=by_polarity, by_waveform=by_waveform,
                    point_noun=aggregate_by, x_col=x_key, x_label=x_label,
                    output_path=out_path)
    return df, points


def main_spec_metrics():
    """Scatter (effect-coloured) of each Y metric in Y_METRIC_SELECTION vs current,
    split by trial type × polarity × waveform."""
    run_spec_metrics(
        trial_types=(COMPARISON_TRIAL_TYPES or None), y_metrics=Y_METRIC_SELECTION,
        heatmap=False, start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS, effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        min_on_trials=COMPARISON_MIN_ON_TRIALS, aggregate_by='spec',
        by_polarity=True, by_waveform=True, save_dir=COMPARISON_SAVE_DIR)


def main_spec_metrics_heatmap():
    """Gaussian-smoothed effect field for each Y metric in Y_METRIC_SELECTION,
    split by trial type × polarity × waveform."""
    run_spec_metrics(
        trial_types=(COMPARISON_TRIAL_TYPES or None), y_metrics=Y_METRIC_SELECTION,
        heatmap=True, start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS, effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        min_on_trials=COMPARISON_MIN_ON_TRIALS, aggregate_by='spec',
        by_polarity=True, by_waveform=True, save_dir=COMPARISON_SAVE_DIR)


def main_halfdist_current_vs_frequency(heatmap=True):
    """Y = corr half-distance, one figure for X = total current and one for
    X = pulse rate (frequency), split by trial type × polarity × waveform."""
    run_spec_metrics(
        trial_types=(COMPARISON_TRIAL_TYPES or None), y_metrics=('half_distance',),
        x_metrics=('total_current_uA', 'pulse_rate_hz'), heatmap=heatmap,
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS, effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        min_on_trials=COMPARISON_MIN_ON_TRIALS, aggregate_by='spec',
        by_polarity=True, by_waveform=True, save_dir=COMPARISON_SAVE_DIR)


# ===========================================================================
# Effect vs the current-per-second : half-distance RATIO.
#
# Collapses the 2-D (current × half-distance) plane onto ONE axis — the ratio
# current_per_second / corr_half_distance — and plots the estim effect directly
# against it, with a 1-D kernel-smoothed curve (Nadaraya–Watson, ± SE band)
# drawn through the points. High ratio = a lot of current relative to how far
# tuning reaches (dose concentrated in a narrow region); low ratio = little
# current spread over a wide region. 2×4 grid: rows = anodic / cathodic,
# columns = trial type.
# ===========================================================================

RATIO_COL = 'current_per_halfdist'
RATIO_LABEL = 'current_per_second ÷ corr half-distance  ((µA·Hz)/µm)'


def _attach_ratio(points, *, x_col='current_per_second', hd_col=HALFDIST_COL,
                  ratio_col=RATIO_COL):
    """Add the current : half-distance ratio column to a points table in place
    (NaN where the half-distance is missing or non-positive)."""
    x = pd.to_numeric(points.get(x_col), errors='coerce').to_numpy(dtype=float)
    hd = pd.to_numeric(points.get(hd_col), errors='coerce').to_numpy(dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        points[ratio_col] = np.where(hd > 0, x / hd, np.nan)
    return points


def _robust_limits(series, *, qlo=1, qhi=99, pad=0.05):
    """Percentile-based (lo, hi) limits — robust to a few ratio outliers that would
    otherwise squash the x-axis — or None."""
    v = pd.to_numeric(series, errors='coerce')
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return None
    lo, hi = float(np.percentile(v, qlo)), float(np.percentile(v, qhi))
    if lo == hi:
        d = abs(lo) or 1.0
        return (lo - 0.5 * d, hi + 0.5 * d)
    m = (hi - lo) * pad
    return (lo - m, hi + m)


def _kernel_smooth_1d(x, y, *, gridsize=160, bw_frac=0.15, xrange=None):
    """1-D Nadaraya–Watson smoothing of y over x with a Gaussian kernel whose
    bandwidth is bw_frac × (robust x-spread). Returns (gx, mean, se) with NaN where
    local support is negligible, or None if < 4 finite points."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 4:
        return None
    spread = (float(np.subtract(*np.percentile(x, [84, 16]))) / 2.0
              or float(np.std(x)) or 1.0)
    h = max(bw_frac * spread, 1e-9)
    lo, hi = (xrange if xrange is not None else (float(x.min()), float(x.max())))
    gx = np.linspace(lo, hi, gridsize)
    d = (gx[:, None] - x[None, :]) / h
    W = np.exp(-0.5 * d * d)
    sw = W.sum(axis=1)
    mean = np.divide((W * y[None, :]).sum(axis=1), sw,
                     out=np.full(gridsize, np.nan), where=sw > 0)
    var = np.divide((W * (y[None, :] - mean[:, None]) ** 2).sum(axis=1), sw,
                    out=np.full(gridsize, np.nan), where=sw > 0)
    neff = np.divide(sw ** 2, (W ** 2).sum(axis=1),
                     out=np.full(gridsize, np.nan), where=sw > 0)
    se = np.sqrt(var / np.clip(neff, 1e-9, None))
    weak = sw < (0.02 * sw.max() if sw.max() > 0 else 0)  # mask ~empty grid regions
    mean[weak] = np.nan
    se[weak] = np.nan
    return gx, mean, se


SIGN_POS_COLOR = '#c0392b'   # red   — smoothed curve of the positive-effect points
SIGN_NEG_COLOR = '#2c6fbb'   # blue  — smoothed curve of the negative-effect points


def plot_effect_vs_ratio_by_trialtype(points, *, trial_types, ratio_col=RATIO_COL,
                                      x_label=RATIO_LABEL, by_polarity=True,
                                      point_noun='spec', bw_frac=0.15,
                                      split_sign=False, output_path=None):
    """2×4 grid (rows = anodic/cathodic, cols = trial type): X = current:half-distance
    ratio, Y = estim effect. Points coloured by effect (house style); shared axis +
    colour limits.

    split_sign=False -> one black kernel-smoothed curve (± SE) through all points,
    signed effect on Y.
    split_sign=True  -> Y is |effect|; a RED curve smoothed over the effect>0 points
    and a BLUE curve over the effect<0 points (each ± SE), both on one positive
    scale so their magnitudes are directly comparable. Dots stay coloured by the
    SIGNED effect."""
    tts = [tt for tt in trial_types if (points['trial_type'] == tt).any()]
    if not tts:
        print("No trial types with points to plot.")
        return None
    row_cols = _resolve_row_cols(points, by_polarity, by_waveform=False)
    groups, row_cols = _row_groups(points, row_cols)

    ncols, nrows = len(tts), len(groups)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 4.2 * nrows),
                             squeeze=False, constrained_layout=True)
    vmax = _effect_vmax(points)
    xlim = _robust_limits(points[ratio_col])
    # split_sign compares |effect| on one positive scale; combined keeps signed Y.
    yseries = pd.to_numeric(points['effect_size'], errors='coerce')
    if split_sign:
        ylim = _axis_limits(yseries.abs())
        if ylim:
            ylim = (0.0, ylim[1])
    else:
        ylim = _axis_limits(yseries)
    y_label = '|estim effect| (ON − OFF %)' if split_sign else 'estim effect (ON − OFF %)'

    def _draw_smooth(ax, xv, yv, color):
        sm = _kernel_smooth_1d(xv, yv, bw_frac=bw_frac, xrange=xlim)
        if sm is None:
            return
        gx, mean, se = sm
        band = np.isfinite(mean) & np.isfinite(se)
        ax.fill_between(gx[band], (mean - se)[band], (mean + se)[band],
                        color=color, alpha=0.15, zorder=3, linewidth=0)
        ax.plot(gx, mean, color=color, lw=2.2, zorder=4)

    scatter_ref = None
    for r, group in enumerate(groups):
        for c, tt in enumerate(tts):
            ax = axes[r][c]
            sub = _filter_rows(points[points['trial_type'] == tt], group)
            sub = sub[[ratio_col, 'effect_size']].dropna()
            x = sub[ratio_col].to_numpy(dtype=float)
            eff = pd.to_numeric(sub['effect_size'], errors='coerce').to_numpy(dtype=float)
            ok = np.isfinite(x) & np.isfinite(eff)
            x, eff = x[ok], eff[ok]
            # split_sign: plot |effect| on Y (both curves on one positive scale) but
            # keep the dots coloured by the SIGNED effect so sign stays visible.
            yv = np.abs(eff) if split_sign else eff

            if not split_sign:
                ax.axhline(0, color='#888888', lw=0.8, ls='--', zorder=1)
            if len(x):
                sc = ax.scatter(x, yv, c=eff, cmap='RdBu_r', vmin=-vmax, vmax=vmax,
                                s=42, alpha=0.85, edgecolors='black', linewidths=0.4,
                                zorder=2)
                scatter_ref = sc
            if split_sign:
                _draw_smooth(ax, x[eff > 0], yv[eff > 0], SIGN_POS_COLOR)
                _draw_smooth(ax, x[eff < 0], yv[eff < 0], SIGN_NEG_COLOR)
            else:
                _draw_smooth(ax, x, yv, 'black')

            lines = []
            if r == 0:
                lines.append(tt)
            if row_cols:
                lines.append(_row_label(group, row_cols))
            lines.append(f"n={len(x)} {point_noun}s")
            ax.set_title("\n".join(lines), fontsize=10)
            if xlim:
                ax.set_xlim(xlim)
            if ylim:
                ax.set_ylim(ylim)
            if r == nrows - 1:
                ax.set_xlabel(x_label, fontsize=9)
            if c == 0:
                ax.set_ylabel(y_label, fontsize=10)
            ax.grid(True, alpha=0.3)

    if scatter_ref is not None:
        cbar = fig.colorbar(scatter_ref, ax=axes.ravel().tolist(), shrink=0.6, pad=0.02)
        cbar.set_label('estim effect (ON − OFF %)  — red = positive, blue = negative',
                       fontsize=10)
    curve_desc = ("Y = |effect|; red = smoothed effect>0 points, "
                  "blue = smoothed effect<0 points"
                  if split_sign else "black = 1-D kernel-smoothed curve ± SE")
    fig.suptitle("Estim effect vs current : corr-half-distance ratio  "
                 f"({curve_desc}"
                 f"{'; rows = ' + ' × '.join(row_cols) if row_cols else ''})",
                 fontsize=14, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved plot to {output_path}")
    plt.show()
    return fig


def run_effect_vs_ratio(trial_types=None, *, start_session_id=None,
                        exclude_session_ids=None, effect_metric=COMPARISON_METRIC,
                        base_required_conditions=None, exclude_other_estim=True,
                        min_on_trials=COMPARISON_MIN_ON_TRIALS,
                        far_fraction=DEFAULT_FAR_FRACTION, near_bins=DEFAULT_NEAR_BINS,
                        bin_agg=DEFAULT_BIN_AGG, smoothing=DEFAULT_SMOOTHING,
                        aggregate_by='spec', by_polarity=True, bw_frac=0.15,
                        x_col='current_per_second', save_dir=None):
    """Build the half-distance table, form the current:half-distance ratio per point,
    and draw the effect-vs-ratio grid. Returns (df, points_df)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] EFFECT vs (current:half-distance) RATIO  trial_types={trial_types}  "
          f"effect_metric={effect_metric}  min_on={min_on_trials}  point={aggregate_by}  "
          f"by_polarity={by_polarity}  bw_frac={bw_frac}")
    df = build_current_spread_halfdist_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions,
        exclude_other_estim=exclude_other_estim, min_on_trials=min_on_trials,
        far_fraction=far_fraction, near_bins=near_bins,
        bin_agg=bin_agg, smoothing=smoothing)
    if len(df) == 0:
        print("Nothing to plot.")
        return df, pd.DataFrame()
    points = build_points(df, [HALFDIST_COL], aggregate_by)
    _attach_ratio(points, x_col=x_col)
    base = f"effect_vs_{_slug(x_col)}_over_halfdist_ratio"
    # Two figures from one table build: the single smoothed curve, and the
    # sign-split version (red curve over effect>0 points, blue over effect<0).
    for split, suffix in ((False, ''), (True, '_by_sign')):
        out_path = (os.path.join(save_dir, f"{base}{suffix}.png") if save_dir else None)
        plot_effect_vs_ratio_by_trialtype(
            points, trial_types=trial_types, by_polarity=by_polarity,
            point_noun=aggregate_by, bw_frac=bw_frac, split_sign=split,
            output_path=out_path)
    return df, points


def main_effect_vs_ratio():
    """Estim effect vs the current_per_second : corr-half-distance ratio, with a 1-D
    kernel-smoothed curve. 2×4 grid (rows = anodic/cathodic, cols = trial type).
    Uses the shared COMPARISON_* config."""
    run_effect_vs_ratio(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        exclude_other_estim=True, min_on_trials=COMPARISON_MIN_ON_TRIALS,
        aggregate_by='spec', by_polarity=True, save_dir=COMPARISON_SAVE_DIR)


def main():
    """Current-spread-vs-tuning grid, one figure per trial type, using the shared
    COMPARISON_* config."""
    # rho above this counts as "high correlation" for the area-of-high-corr row.
    high_corr_threshold = DEFAULT_HIGH_CORR_THRESHOLD
    # Probe scales shown as columns (n_neighbors): local / half-probe / whole-probe.
    scales = DEFAULT_SCALES

    run_current_spread_vs_tuning(
        trial_types=(COMPARISON_TRIAL_TYPES or None),  # None/[] -> auto-discover
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        scales=scales,
        threshold=high_corr_threshold,
        exclude_other_estim=True,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        save_dir=COMPARISON_SAVE_DIR,
    )


if __name__ == '__main__':
    #   - main()                      -> current vs tuning grid (scatter)
    #   - main_half_distance()        -> correlation half-distance vs current (scatter)
    #   - main_half_distance_heatmap()-> smoothed effect field over current ×
    #                                    correlation half-distance
    #   - main_tuning_heatmap()       -> smoothed effect field of the tuning grid
    #   - main_symmetry()             -> tuning-region symmetry offset vs current
    #                                    (scatter, effect-coloured)
    #   - main_symmetry_heatmap()     -> smoothed effect field over current ×
    #                                    symmetry offset
    #   - main_corr_in_half_distance() / _heatmap() -> correlation strength within
    #                                    the half-distance vs current
    #
    # PREFERRED entry — one table, one file per Y metric in Y_METRIC_SELECTION
    # (edit that tuple / the Y_METRICS registry to choose the y-axis metric):
    #   - main_spec_metrics_heatmap() -> smoothed effect field per selected metric
    #   - main_spec_metrics()         -> effect-coloured scatter per selected metric
    #   - main_halfdist_current_vs_frequency() -> corr half-distance heatmaps with
    #                                    X = total current AND X = frequency (2 figs)
    #   - main_effect_vs_ratio()      -> estim effect vs current:half-distance ratio,
    #                                    1-D smoothed curve; 2×4 (polarity × trial type)
    main_effect_vs_ratio()
    # main_halfdist_current_vs_frequency()
    # main_spec_metrics_heatmap()
    # main_spec_metrics()
    # main_corr_in_half_distance_heatmap()
    # main_symmetry_heatmap()
    # main_half_distance_heatmap()
    # main_half_distance()
    # main_tuning_heatmap()
    # main()

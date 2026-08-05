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

    X = current spread   (for now: current_per_second = a1 x num_channels x
                          pulse_rate_hz, per spec)
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

Run this file to produce one figure per trial type (uses the shared COMPARISON_*
config in analyze_estim_isolation_effect). Needs the GA response vectors that
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

# The stored channel-correlation metric (Spearman rho of ga_mean_response vectors)
# whose per-pair values we re-aggregate three ways.
CORR_METRIC_NAME = 'channel_corr'

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

X_COLUMN = 'current_per_second'
X_LABEL = 'current spread  (current_per_second, µA·Hz)'


def _metric_col(family, n_neighbors):
    return f"{family}__n{int(n_neighbors)}"


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
    agg_map = {X_COLUMN: (X_COLUMN, 'mean'),
               'effect_size': ('effect_size', 'mean')}
    agg_map.update({c: (c, 'mean') for c in metric_cols})
    agg_map['n_specs'] = ('estim_spec_id', 'size')
    return (df.groupby(['trial_type', 'session_id'], as_index=False)
              .agg(**agg_map))


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
    keep = (['trial_type', 'session_id', 'estim_spec_id', X_COLUMN, 'effect_size']
            + list(metric_cols))
    keep = [c for c in keep if c in df.columns]
    return df[keep].copy()


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_current_spread_vs_tuning_for_trial_type(agg_tt, *, scales=DEFAULT_SCALES,
                                                 threshold=DEFAULT_HIGH_CORR_THRESHOLD,
                                                 trial_type='', point_noun='spec',
                                                 output_path=None):
    """Grid of tuning-family (rows) x probe-scale (cols) panels for one trial type.
    One point per `point_noun` (spec/condition by default); X = current_per_second,
    Y = the tuning metric, colour = estim effect."""
    scale_items = sorted(scales.items(), key=lambda kv: kv[1])  # (label, n) low->high
    nrows, ncols = len(FAMILIES), len(scale_items)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.6 * ncols, 4.0 * nrows),
                             squeeze=False, constrained_layout=True)

    # Symmetric diverging colour scale for the estim effect (red = positive,
    # blue = negative), shared across every panel.
    eff_all = pd.to_numeric(agg_tt.get('effect_size'), errors='coerce')
    finite_eff = eff_all[np.isfinite(eff_all)] if eff_all is not None else pd.Series([], dtype=float)
    vmax = max(float(np.abs(finite_eff).max()), 1e-6) if len(finite_eff) else 1.0

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
                                 aggregate_by='spec', save_dir=None):
    """Build the table and draw one figure per trial type. trial_types=None
    auto-discovers them. aggregate_by='spec' (default) plots one point per estim
    spec/condition (keeps each condition's own current); 'experiment' averages per
    session. Returns (per_spec_df, points_df)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] CURRENT-SPREAD vs TUNING  trial_types={trial_types}  "
          f"effect_metric={effect_metric}  scales={scales}  threshold={threshold}  "
          f"min_on={min_on_trials}  point={aggregate_by}")

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
    for tt in trial_types:
        pts_tt = points[points['trial_type'] == tt]
        if len(pts_tt) == 0:
            print(f"  (no {aggregate_by}s for trial_type={tt!r})")
            continue
        print(f"\n=== {tt}: {len(pts_tt)} {aggregate_by}s ===")
        out_path = (os.path.join(save_dir, f"current_spread_vs_tuning_{_slug(tt)}.png")
                    if save_dir else None)
        plot_current_spread_vs_tuning_for_trial_type(
            pts_tt, scales=scales, threshold=threshold, trial_type=tt,
            point_noun=aggregate_by, output_path=out_path)
    return df, points


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
    main()

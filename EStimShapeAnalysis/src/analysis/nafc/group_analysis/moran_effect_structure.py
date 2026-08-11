"""
Is the estim effect spatially structured in (current_per_second × corr
half-distance) space? — Moran's I with a within-session permutation null.

The heatmaps in ``plot_current_spread_vs_tuning`` *suggest* that positive and
negative estim effects occupy different regions of the (current, tuning-geometry)
plane, but a smoothed field is a hypothesis generator, not a test. This module
tests the shape-agnostic hypothesis:

    H0: a spec's effect is unrelated to WHERE it sits in
        (current_per_second, corr_half_distance) space (effects are randomly
        arranged over the plane).
    H1: nearby specs in that plane have more similar effects than chance —
        i.e. there is spatial structure (a gradient OR distinct patches; we make
        no claim about the shape).

**Statistic.** Moran's I of the signed effect over a Gaussian spatial-weights
graph built on the standardised (current, half-distance) coordinates
(row-standardised weights, zero diagonal). Positive I = spatial autocorrelation =
structure.

**Null — within-session permutation (the honest one).** Specs from one session
share tissue and share current/geometry settings, so they cluster in the plane
AND their effects are correlated for session-level reasons. A global label shuffle
would flag that session confound as "structure". Instead we permute effects ONLY
among specs of the SAME session: the positions stay fixed, each session keeps its
own set of effect values, and cross-session clustering is preserved — so the test
only detects structure BEYOND session identity. (This needs multiple specs per
session to have power; the printout reports how shuffleable each group is.)

The test is run as an INDEPENDENT test per group — by default every present
combination of trial_type × polarity × waveform — since the effect's meaning and
the biophysics differ across those conditions. (Many 3-way cells will be small;
groups below MORAN_MIN_N specs are skipped, and with many cells keep the
multiplicity in mind.) p is one-sided (positive autocorrelation):
    p = (1 + #{I_perm >= I_obs}) / (n_perm + 1).

The plot pairs, for each group, the raw data (current vs half-distance coloured
by effect) with the permutation null histogram and the observed I, so you see
exactly what is being tested and how far the observed value sits in the tail.

Run this file (uses the shared COMPARISON_* config). Reports a table and one
figure. A short bandwidth-sensitivity table is printed so the result isn't
resting on a single kernel width.
"""

import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from src.analysis.nafc.group_analysis.plot_current_spread_vs_tuning import (
    build_spec_metric_table, build_points, HALFDIST_COL, X_LABELS, _slug,
)
from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
    COMPARISON_METRIC,
    COMPARISON_REQUIRED_CONDITIONS,
    COMPARISON_START_SESSION_ID,
    COMPARISON_EXCLUDE_SESSION_IDS,
    COMPARISON_MIN_ON_TRIALS,
    COMPARISON_TRIAL_TYPES,
    COMPARISON_SAVE_DIR,
    _discover_trial_types,
)

# Gaussian spatial-weight bandwidth in STANDARDISED-distance units (each axis is
# z-scored first, so ~0.5 means "half a standard deviation away in the plane").
MORAN_BANDWIDTH = 0.5
MORAN_BANDWIDTH_SWEEP = (0.3, 0.5, 0.8)   # printed sensitivity check
MORAN_N_PERM = 5000
MORAN_MIN_N = 8                           # skip groups smaller than this
MORAN_SEED = 0

VALUE_COL = 'effect_size'

# LISA cluster categories (from signs of a spec's own deviation and its neighbours'
# mean deviation, kept only where the local Moran's I is significant).
LISA_ALPHA = 0.05
CLUSTER_ORDER = ('HH', 'LL', 'HL', 'LH', 'ns')
CLUSTER_LABELS = {
    'HH': 'high–high (positive pocket)',
    'LL': 'low–low (negative pocket)',
    'HL': 'high–low (positive outlier)',
    'LH': 'low–high (negative outlier)',
    'ns': 'not significant',
}
CLUSTER_COLORS = {
    'HH': '#D7191C', 'LL': '#2C7BB6', 'HL': '#FDAE61', 'LH': '#ABD9E9',
    'ns': '#dddddd',
}


# ---------------------------------------------------------------------------
# Moran's I + within-session permutation
# ---------------------------------------------------------------------------

def _standardize(a):
    """z-score, or None if the column is constant."""
    a = np.asarray(a, dtype=float)
    sd = float(np.std(a))
    if sd < 1e-12:
        return None
    return (a - float(np.mean(a))) / sd


def _row_standardized_gaussian_weights(coords, bandwidth):
    """Row-standardised Gaussian weights over standardised 2-D coords (zero
    diagonal). w_ij ∝ exp(-½ ||zi-zj||² / bw²); each row sums to 1."""
    diff = coords[:, None, :] - coords[None, :, :]
    d2 = (diff * diff).sum(axis=-1)
    W = np.exp(-0.5 * d2 / (bandwidth ** 2))
    np.fill_diagonal(W, 0.0)
    rowsum = W.sum(axis=1, keepdims=True)
    rowsum[rowsum == 0] = 1.0
    return W / rowsum


def _morans_i(values, W):
    """Moran's I of `values` over weights `W`."""
    z = values - values.mean()
    den = float((z * z).sum())
    if den <= 0:
        return np.nan
    num = float(z @ (W @ z))
    n = len(values)
    s0 = float(W.sum())
    if s0 <= 0:
        return np.nan
    return (n / s0) * num / den


def _local_morans(values, W, *, mean=None, m2=None):
    """Local Moran's I vector (Anselin 1995) plus the value deviations z and the
    spatial lag. I_i = (z_i / m2) · Σ_j w_ij z_j. mean/m2 may be passed in (they are
    invariant under permutation of `values`, so precomputing saves work)."""
    z = values - (values.mean() if mean is None else mean)
    if m2 is None:
        m2 = float((z * z).mean())
    lag = W @ z
    local = (z / m2) * lag if m2 > 0 else np.full_like(z, np.nan)
    return local, z, lag


def _within_session_null_full(values, session_ids, W, n_perm, seed):
    """Within-session permutation null for BOTH the global Moran's I (per perm) and
    the local Moran's I of every spec (per perm), from one shared permutation loop.
    Effects are shuffled only among specs sharing a session; positions/weights fixed.

    The value set is unchanged by permutation, so the mean, Σz², m² and S0 are all
    invariant — only the arrangement (z @ W z, and the per-i lag) changes.
    Returns (global_null[n_perm], local_null[n_perm, N])."""
    rng = np.random.default_rng(seed)
    by_session = {}
    for i, s in enumerate(session_ids):
        by_session.setdefault(s, []).append(i)
    idx_groups = [np.asarray(v) for v in by_session.values() if len(v) > 1]

    n = len(values)
    mean = float(values.mean())
    zc = values - mean
    den = float((zc * zc).sum())          # Σ z²  (invariant)
    m2 = den / n                           # variance (invariant)
    s0 = float(W.sum())                    # Σ w    (invariant)
    g_null = np.empty(n_perm, dtype=float)
    l_null = np.empty((n_perm, n), dtype=float)
    for p in range(n_perm):
        perm = values.copy()
        for g in idx_groups:
            perm[g] = values[g][rng.permutation(len(g))]
        z = perm - mean
        lag = W @ z
        g_null[p] = (n / s0) * float(z @ lag) / den if (den > 0 and s0 > 0) else np.nan
        l_null[p] = (z / m2) * lag if m2 > 0 else np.nan
    return g_null, l_null


def morans_test_for_group(sub, *, x_col, y_col=HALFDIST_COL, value_col=VALUE_COL,
                          bandwidth=MORAN_BANDWIDTH, n_perm=MORAN_N_PERM, seed=MORAN_SEED):
    """Run the within-session permutation Moran's I test on one group's specs.
    Returns a dict with I, z, p, the null, the raw data, and diagnostics — or None
    if too few / degenerate."""
    d = sub[[x_col, y_col, value_col, 'session_id']].dropna()
    n = len(d)
    if n < MORAN_MIN_N:
        return None
    xz = _standardize(d[x_col].to_numpy())
    yz = _standardize(d[y_col].to_numpy())
    if xz is None or yz is None:
        return None
    coords = np.column_stack([xz, yz])
    vals = d[value_col].to_numpy(dtype=float)
    W = _row_standardized_gaussian_weights(coords, bandwidth)
    i_obs = _morans_i(vals, W)
    if not np.isfinite(i_obs):
        return None

    # One permutation loop yields both the global null and every spec's local null.
    g_null, l_null = _within_session_null_full(
        vals, d['session_id'].to_numpy(), W, n_perm, seed)
    p_one = (1.0 + float(np.sum(g_null >= i_obs))) / (n_perm + 1)
    null_sd = float(np.std(g_null))
    z = (i_obs - float(np.mean(g_null))) / (null_sd if null_sd > 1e-12 else 1.0)

    # --- LISA: local Moran's I + significance + quadrant clusters ---
    local_obs, z_dev, lag = _local_morans(vals, W)
    # Pseudo p per spec, one-sided in the observed direction (HH/LL -> upper tail,
    # HL/LH -> lower tail), from that spec's own permutation null.
    ge = (l_null >= local_obs[None, :]).sum(axis=0)
    le = (l_null <= local_obs[None, :]).sum(axis=0)
    tail = np.where(local_obs >= 0, ge, le)
    p_local = (1.0 + tail) / (n_perm + 1)
    clusters = np.array(['ns'] * n, dtype=object)
    sig = p_local < LISA_ALPHA
    pos_z, pos_lag = z_dev > 0, lag > 0
    clusters[sig & pos_z & pos_lag] = 'HH'
    clusters[sig & ~pos_z & ~pos_lag] = 'LL'
    clusters[sig & pos_z & ~pos_lag] = 'HL'
    clusters[sig & ~pos_z & pos_lag] = 'LH'
    cluster_counts = {c: int((clusters == c).sum()) for c in CLUSTER_ORDER}

    counts = d['session_id'].value_counts()
    return {
        'n': int(n),
        'n_sessions': int(d['session_id'].nunique()),
        'n_shuffleable': int((counts > 1).sum()),         # sessions with >1 spec
        'frac_in_multi': float((counts[counts > 1].sum()) / n),  # specs in shuffleable sessions
        'I': float(i_obs),
        'E_null': float(np.mean(g_null)),
        'z': float(z),
        'p': float(p_one),
        'null': g_null,
        'x': d[x_col].to_numpy(dtype=float),
        'y': d[y_col].to_numpy(dtype=float),
        'eff': vals,
        'local_I': local_obs,
        'p_local': p_local,
        'clusters': clusters,
        'cluster_counts': cluster_counts,
    }


# ---------------------------------------------------------------------------
# Grouping helper
# ---------------------------------------------------------------------------

# Short labels for the categorical split columns (trial_type kept verbatim).
_SHORT = {
    'polarity': {'PositiveFirst': 'anodic', 'NegativeFirst': 'cathodic'},
    'waveform': {'Biphasic': 'biphasic',
                 'BiphasicWithInterphaseDelay': 'biphasic+delay',
                 'Triphasic': 'triphasic'},
}


def _val_label(col, val):
    return _SHORT.get(col, {}).get(val, str(val))


def _iter_groups(points, group_by):
    """Yield (label, subframe) for each present combination of the group_by columns
    (empty group_by -> one 'all' group). Each combination is an INDEPENDENT test."""
    group_by = [c for c in group_by if c in points.columns]
    if not group_by:
        yield 'all', points
        return
    combos = points[group_by].dropna().drop_duplicates()
    for _, row in combos.iterrows():
        mask = np.ones(len(points), dtype=bool)
        for c in group_by:
            mask &= (points[c] == row[c]).to_numpy()
        label = " · ".join(_val_label(c, row[c]) for c in group_by)
        yield label, points[mask]


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_moran_results(results, *, x_label, y_label, bandwidth, output_path=None):
    """One row per group: left = data scatter (current vs half-distance coloured by
    effect), right = within-session permutation null of Moran's I with the observed
    value marked. `results` is a list of (label, result-dict)."""
    results = [(lab, r) for lab, r in results if r is not None]
    if not results:
        print("No groups with a Moran's I result to plot.")
        return None
    nrows = len(results)
    fig, axes = plt.subplots(nrows, 2, figsize=(11, 3.6 * nrows),
                             squeeze=False, constrained_layout=True)

    all_eff = np.concatenate([r['eff'] for _, r in results])
    vmax = max(float(np.abs(all_eff).max()), 1e-6)

    scatter_ref = None
    for r_i, (label, res) in enumerate(results):
        ax_s, ax_h = axes[r_i][0], axes[r_i][1]

        sc = ax_s.scatter(res['x'], res['y'], c=res['eff'], cmap='RdBu_r',
                          vmin=-vmax, vmax=vmax, s=55, alpha=0.9,
                          edgecolors='black', linewidths=0.5)
        scatter_ref = sc
        ax_s.set_ylabel(y_label, fontsize=9)
        if r_i == nrows - 1:
            ax_s.set_xlabel(x_label, fontsize=9)
        ax_s.set_title(f"{label}\nn={res['n']} specs, {res['n_sessions']} sessions "
                       f"({res['n_shuffleable']} shuffleable)", fontsize=10)
        ax_s.grid(True, alpha=0.3)

        ax_h.hist(res['null'], bins=40, color='#b0b0b0', edgecolor='none')
        ax_h.axvline(res['E_null'], color='black', linestyle='--', linewidth=1,
                     label=f"null mean ({res['E_null']:+.3f})")
        ax_h.axvline(res['I'], color='red', linewidth=2.5,
                     label=f"observed I ({res['I']:+.3f})")
        sig = '★' if res['p'] < 0.05 else ''
        ax_h.set_title(f"Moran's I = {res['I']:+.3f}   z = {res['z']:+.2f}   "
                       f"p = {res['p']:.4f} {sig}", fontsize=10)
        if r_i == nrows - 1:
            ax_h.set_xlabel("Moran's I (within-session permutation null)", fontsize=9)
        ax_h.set_ylabel('permutations', fontsize=9)
        ax_h.legend(fontsize=8, framealpha=0.9)
        ax_h.grid(True, axis='y', alpha=0.3)

    if scatter_ref is not None:
        cbar = fig.colorbar(scatter_ref, ax=axes[:, 0].tolist(), shrink=0.6, pad=0.02)
        cbar.set_label('estim effect (ON − OFF %)', fontsize=9)

    fig.suptitle("Spatial structure of estim effect in (current × corr half-distance) "
                 f"space — Moran's I, within-session permutation (bw={bandwidth})",
                 fontsize=13, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved Moran's I figure to {output_path}")
    plt.show()
    return fig


def plot_lisa_maps(results, *, x_label, y_label, bandwidth, alpha=LISA_ALPHA,
                   output_path=None):
    """LISA cluster map per group: specs in (current × half-distance) space coloured
    by local-Moran cluster — HH (positive pocket), LL (negative pocket), HL/LH
    (outliers), or not-significant. Reveals disconnected consistent pockets that a
    single global I can dilute. `results` is a list of (label, result-dict)."""
    from matplotlib.lines import Line2D
    results = [(lab, r) for lab, r in results if r is not None]
    if not results:
        print("No groups with a LISA result to plot.")
        return None
    n = len(results)
    ncols = min(3, n)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.0 * ncols, 4.3 * nrows),
                             squeeze=False, constrained_layout=True)

    for i, (label, res) in enumerate(results):
        ax = axes[i // ncols][i % ncols]
        clusters = res['clusters']
        for cat in CLUSTER_ORDER:
            m = clusters == cat
            if not m.any():
                continue
            ax.scatter(res['x'][m], res['y'][m], s=(38 if cat == 'ns' else 70),
                       color=CLUSTER_COLORS[cat], alpha=(0.5 if cat == 'ns' else 0.95),
                       edgecolors='black', linewidths=0.4, zorder=(1 if cat == 'ns' else 3))
        cc = res['cluster_counts']
        counts_txt = "  ".join(f"{c}:{cc[c]}" for c in ('HH', 'LL', 'HL', 'LH') if cc[c])
        ax.set_title(f"{label}\nn={res['n']}, I={res['I']:+.3f} p={res['p']:.3f}"
                     f"{('   ' + counts_txt) if counts_txt else '   (no sig. pockets)'}",
                     fontsize=9)
        if i // ncols == nrows - 1:
            ax.set_xlabel(x_label, fontsize=9)
        if i % ncols == 0:
            ax.set_ylabel(y_label, fontsize=9)
        ax.grid(True, alpha=0.3)

    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis('off')

    legend_handles = [
        Line2D([0], [0], marker='o', linestyle='None', markersize=9,
               markerfacecolor=CLUSTER_COLORS[c], markeredgecolor='black',
               label=CLUSTER_LABELS[c])
        for c in CLUSTER_ORDER]
    fig.legend(handles=legend_handles, loc='lower center', ncol=len(CLUSTER_ORDER),
               fontsize=9, framealpha=0.9, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Local Moran's I (LISA) cluster map — significant consistent pockets "
                 f"(within-session null, α={alpha}, bw={bandwidth})",
                 fontsize=13, fontweight='bold')
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        fig.savefig(output_path.rsplit('.', 1)[0] + '.svg', bbox_inches='tight')
        print(f"Saved LISA map to {output_path}")
    plt.show()
    return fig


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_moran_test(trial_types=None, *, x_col='current_per_second', y_col=HALFDIST_COL,
                   group_by=('trial_type', 'polarity', 'waveform'),
                   bandwidth=MORAN_BANDWIDTH,
                   bandwidth_sweep=MORAN_BANDWIDTH_SWEEP, n_perm=MORAN_N_PERM,
                   seed=MORAN_SEED, start_session_id=None, exclude_session_ids=None,
                   effect_metric=COMPARISON_METRIC, base_required_conditions=None,
                   min_on_trials=COMPARISON_MIN_ON_TRIALS, save_dir=None):
    """Build the per-spec table, run the within-session permutation Moran's I test
    per group, print a results + bandwidth-sensitivity table, and plot. Returns
    (results_df, results_list)."""
    if trial_types is None:
        trial_types = _discover_trial_types(start_session_id, exclude_session_ids)
    print(f"[config] MORAN'S I  x={x_col}  y={y_col}  group_by={list(group_by)}  "
          f"bandwidth={bandwidth}  n_perm={n_perm}  min_on={min_on_trials}")

    df = build_spec_metric_table(
        trial_types, start_session_id=start_session_id,
        exclude_session_ids=exclude_session_ids, effect_metric=effect_metric,
        base_required_conditions=base_required_conditions, min_on_trials=min_on_trials)
    if len(df) == 0:
        print("Nothing to test.")
        return pd.DataFrame(), []
    points = build_points(df, [y_col], aggregate_by='spec')

    results, rows = [], []
    for gi, (label, sub) in enumerate(_iter_groups(points, group_by)):
        res = morans_test_for_group(
            sub, x_col=x_col, y_col=y_col, bandwidth=bandwidth, n_perm=n_perm,
            seed=seed + gi)
        results.append((label, res))
        if res is None:
            print(f"\n[{label}] skipped (n<{MORAN_MIN_N} or degenerate)")
            continue
        # Bandwidth sensitivity (same within-session null, different kernel width).
        sweep = {}
        for bw in bandwidth_sweep:
            rb = morans_test_for_group(sub, x_col=x_col, y_col=y_col, bandwidth=bw,
                                       n_perm=n_perm, seed=seed + gi)
            if rb is not None:
                sweep[bw] = (rb['I'], rb['p'])
        cc = res['cluster_counts']
        rows.append({
            'group': label, 'n': res['n'], 'n_sessions': res['n_sessions'],
            'n_shuffleable': res['n_shuffleable'],
            'frac_in_multi': round(res['frac_in_multi'], 2),
            'I': round(res['I'], 4), 'z': round(res['z'], 2), 'p': round(res['p'], 4),
            'HH': cc['HH'], 'LL': cc['LL'], 'HL': cc['HL'], 'LH': cc['LH'],
            **{f"I@bw{bw}": round(v[0], 3) for bw, v in sweep.items()},
            **{f"p@bw{bw}": round(v[1], 4) for bw, v in sweep.items()},
        })
        print(f"\n[{label}] n={res['n']} ({res['n_sessions']} sessions, "
              f"{res['n_shuffleable']} shuffleable, "
              f"{res['frac_in_multi']*100:.0f}% of specs in multi-spec sessions)")
        print(f"    Moran's I = {res['I']:+.4f}  (null mean {res['E_null']:+.4f})  "
              f"z = {res['z']:+.2f}  p(one-sided) = {res['p']:.4f}")
        if res['frac_in_multi'] < 0.5:
            print("    WARNING: <50% of specs are in multi-spec sessions — the "
                  "within-session null has little permutation freedom, so power is low.")
        if sweep:
            print("    bandwidth sensitivity: "
                  + "  ".join(f"bw{bw}: I={v[0]:+.3f} p={v[1]:.3f}"
                              for bw, v in sweep.items()))

    board = pd.DataFrame(rows)
    if len(board):
        print("\n=== Moran's I summary ===")
        with pd.option_context('display.width', 200, 'display.max_columns', None):
            print(board.to_string(index=False))

    x_label = X_LABELS.get(x_col, x_col)
    out_path = (os.path.join(save_dir, f"morans_i_effect_structure_vs_{_slug(x_col)}.png")
                if save_dir else None)
    plot_moran_results(results, x_label=x_label,
                       y_label='corr half-distance (µm)', bandwidth=bandwidth,
                       output_path=out_path)
    lisa_path = (os.path.join(save_dir, f"lisa_effect_clusters_vs_{_slug(x_col)}.png")
                 if save_dir else None)
    plot_lisa_maps(results, x_label=x_label, y_label='corr half-distance (µm)',
                   bandwidth=bandwidth, output_path=lisa_path)
    return board, results


def main():
    """Within-session permutation Moran's I of the estim effect in
    (current_per_second × corr half-distance) space, per trial type. Uses the
    shared COMPARISON_* config."""
    run_moran_test(
        trial_types=(COMPARISON_TRIAL_TYPES or None),
        x_col='current_per_second', y_col=HALFDIST_COL,
        # Independent test per trial_type × polarity × waveform. Trim this tuple
        # (e.g. ('trial_type',)) if the 3-way split leaves groups too small.
        group_by=('trial_type', 'polarity', 'waveform'),
        bandwidth=MORAN_BANDWIDTH, n_perm=MORAN_N_PERM,
        start_session_id=COMPARISON_START_SESSION_ID,
        exclude_session_ids=COMPARISON_EXCLUDE_SESSION_IDS,
        effect_metric=COMPARISON_METRIC,
        base_required_conditions=COMPARISON_REQUIRED_CONDITIONS or None,
        min_on_trials=COMPARISON_MIN_ON_TRIALS,
        save_dir=COMPARISON_SAVE_DIR,
    )


if __name__ == '__main__':
    main()

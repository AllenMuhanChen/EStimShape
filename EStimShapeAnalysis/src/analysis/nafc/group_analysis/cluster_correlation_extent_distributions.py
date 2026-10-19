"""
GA cluster correlation extent across experiments (the per-session figure is
plot_cluster_correlation_spread, which defines the metric).

For every session: each channel's Spearman (or Pearson) ρ with the average GA cluster response
(GA channels leave-one-out), then the contiguous extent at a fixed ρ threshold walked up and
down the probe (stops after N_MISSES_TO_STOP channels in a row below ρ threshold).

Figure, one value per session unless noted:
  A. histogram of the total extent (µm). With split_probe_end, sessions where a side
     reaches the end of the probe are stacked in a separate colour (their extent is a
     lower bound).
  B. one value per channel, pooled over sessions: overlaid histograms of ρ for GA
     channels (each vs the other GA channels of its session; sessions with a single GA
     channel have none) and non-GA channels (vs the GA response). With
     normalize_channel_hist each group sums to 1, since there are far more non-GA
     channels than GA channels.
  C. every non-GA channel with data, pooled over sessions: distance along the probe to
     the nearest GA channel vs its ρ with the GA response, with the binned median and
     interquartile range (bins = probe pitch).

Outputs go to a timestamped folder: config.json, sessions.csv (one row per session),
channels.csv (one row per session x channel), cluster_corr_extent_distributions.png/.svg.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.nafc.group_analysis import plot_cluster_correlation_spread as ccs
from src.analysis.nafc.group_analysis.analyze_estim_isolation_effect import (
    COMPARISON_EXCLUDE_SESSION_IDS, COMPARISON_START_SESSION_ID)

EXTENT_COLOR = "#2a78d6"
PROBE_END_COLOR = "#f0a030"
GA_RHO_COLOR = "#2a9d6f"
NON_GA_RHO_COLOR = "#8a8a8a"
THRESHOLD_COLOR = "tab:red"


def all_estim_session_ids():
    """Every session_id in EStimShapeTrials, sorted."""
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM EStimShapeTrials ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]


def select_sessions(session_ids, start_session_id, exclude_session_ids):
    if session_ids is None:
        session_ids = all_estim_session_ids()
    if start_session_id:
        session_ids = [s for s in session_ids if s >= start_session_id]
    return [s for s in session_ids if s not in set(exclude_session_ids or ())]


def session_rows(session_id, rho_n, channel_strs, positions_um, ga_strs, *,
                 rho_threshold, n_misses_to_stop):
    """(session row dict, [channel row dicts]) for one session."""
    ext = ccs.contiguous_extent(channel_strs, positions_um, rho_n, ga_strs,
                                rho_threshold=rho_threshold,
                                n_misses_to_stop=n_misses_to_stop)
    pos = np.asarray(positions_um, dtype=float)
    ga_pos = np.array([pos[i] for i, ch in enumerate(channel_strs) if ch in ga_strs])
    ga_rhos = [rho_n[g][0] for g in ga_strs if np.isfinite(rho_n[g][0])]
    non_ga_rhos = [r for ch, (r, _) in rho_n.items()
                   if ch not in ga_strs and ch in channel_strs and np.isfinite(r)]

    channels = []
    for i, ch in enumerate(channel_strs):
        rho, n = rho_n.get(ch, (np.nan, 0))
        if not np.isfinite(rho):
            continue
        channels.append({'session_id': session_id, 'channel': ch,
                         'is_ga': ch in ga_strs, 'rho': rho, 'n_stimuli': n,
                         'distance_to_ga_um': float(np.min(np.abs(ga_pos - pos[i])))})
    session = {
        'session_id': session_id, 'ga_channels': ','.join(ga_strs),
        'n_ga_channels': len(ga_strs),
        'avg_ga_rho': float(np.mean(ga_rhos)) if ga_rhos else np.nan,
        'avg_non_ga_rho': float(np.mean(non_ga_rhos)) if non_ga_rhos else np.nan,
        'extent_total_um': ext['extent_total_um'],
        'extent_up_um': ext['extent_up_um'], 'extent_down_um': ext['extent_down_um'],
        'up_reached_probe_end': ext['up_reached_end'],
        'down_reached_probe_end': ext['down_reached_end'],
        'reaches_probe_end': ext['up_reached_end'] or ext['down_reached_end'],
    }
    return session, channels


def build_tables(session_ids, *, rho_threshold, n_misses_to_stop, method, vector_type):
    """(sessions DataFrame, channels DataFrame, {session_id: reason skipped})."""
    sessions, channels, skipped = [], [], {}
    for sid in session_ids:
        try:
            rho_n, channel_strs, positions_um, ga_strs = ccs.load_session_rhos(
                sid, method=method, vector_type=vector_type)
        except RuntimeError as e:  # no response vectors / no GA channels with data
            skipped[sid] = str(e)
            print(f"SKIPPED {e}")
            continue
        s_row, c_rows = session_rows(sid, rho_n, channel_strs, positions_um, ga_strs,
                                     rho_threshold=rho_threshold,
                                     n_misses_to_stop=n_misses_to_stop)
        sessions.append(s_row)
        channels.extend(c_rows)
        print(f"{sid}: extent = {s_row['extent_total_um']:.0f} µm"
              f"{' (probe end)' if s_row['reaches_probe_end'] else ''}, "
              f"avg GA ρ = {s_row['avg_ga_rho']:.2f}")
    return pd.DataFrame(sessions), pd.DataFrame(channels), skipped


def _pitch(channels):
    d = np.unique(channels['distance_to_ga_um'].to_numpy())
    d = np.diff(d[d >= 0])
    return float(d[d > 0].min()) if np.any(d > 0) else 65.0


def plot_extent_hist(ax, sessions, bin_width, split_probe_end):
    """bin_width in µm; bins are centred on multiples of bin_width (extents are
    multiples of the probe pitch, so a multiple of the pitch keeps them centred)."""
    vals = sessions['extent_total_um'].to_numpy(dtype=float)
    end = sessions['reaches_probe_end'].to_numpy(dtype=bool)
    bins = np.arange(-bin_width / 2, vals.max() + bin_width, bin_width)
    if split_probe_end:
        ax.hist([vals[~end], vals[end]], bins=bins, stacked=True,
                color=[EXTENT_COLOR, PROBE_END_COLOR], edgecolor='white', lw=0.8)
    else:
        ax.hist(vals, bins=bins, color=EXTENT_COLOR, edgecolor='white', lw=0.8)
    med = np.median(vals)
    ax.axvline(med, color='black', lw=1.8, ls='--')
    ax.set_xlabel('Cluster extent (µm)', fontsize=13)
    ax.set_ylabel('Number of experiments', fontsize=13)
    ax.set_title('Correlation extent', fontsize=14, fontweight='bold')
    ax.yaxis.get_major_locator().set_params(integer=True)
    handles = [Line2D([0], [0], color='black', ls='--', lw=1.8,
                      label=f'median = {med:.0f} µm')]
    if split_probe_end:
        handles = [Patch(color=EXTENT_COLOR, label='within probe'),
                   Patch(color=PROBE_END_COLOR, label='reaches probe end')] + handles
    ax.legend(handles=handles, fontsize=11, frameon=False, loc='upper right')


def plot_channel_rho_hist(ax, channels, rho_threshold, bin_width, normalize,
                          method='spearman'):
    """Overlaid histograms of ρ, one value per channel: GA channels (vs the other GA
    channels) and non-GA channels (vs the GA response). normalize -> each group's bars
    sum to 1 (fraction of that group's channels)."""
    bins = np.arange(-1, 1 + bin_width, bin_width)
    handles = []
    for is_ga, color, label in ((False, NON_GA_RHO_COLOR, 'non-GA channels'),
                                (True, GA_RHO_COLOR, 'GA channels')):
        vals = channels.loc[channels['is_ga'] == is_ga, 'rho'].dropna().to_numpy(float)
        if not len(vals):
            continue
        weights = np.full(len(vals), 1 / len(vals)) if normalize else None
        ax.hist(vals, bins=bins, weights=weights, color=color, alpha=0.65,
                edgecolor='white', lw=0.8)
        med = np.median(vals)
        ax.axvline(med, color=color, lw=2, ls=':', ymax=0.72)  # stop below legend
        handles.append(Patch(color=color, alpha=0.65,
                             label=f'{label} (n = {len(vals)}, median {med:.2f})'))
    ax.axvline(rho_threshold, color=THRESHOLD_COLOR, lw=2, ls='--', ymax=0.72)
    handles.append(Line2D([0], [0], color=THRESHOLD_COLOR, ls='--', lw=2,
                          label=f'ρ threshold = {rho_threshold:.2f}'))
    ax.set_xlim(-0.5, 1)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.35)  # headroom so the legend clears the bars
    ax.set_xlabel(f'{ccs.method_name(method)} ρ with GA cluster response', fontsize=13)
    ax.set_ylabel('Fraction of channels' if normalize else 'Number of channels',
                  fontsize=13)
    ax.set_title('GA vs non-GA channel correlation', fontsize=14, fontweight='bold')
    ax.legend(handles=handles, fontsize=11, frameon=False, loc='upper left')


def plot_distance_scatter(ax, channels, rho_threshold, pitch, jitter_um, rng,
                          method='spearman'):
    other = channels[~channels['is_ga']]
    d = other['distance_to_ga_um'].to_numpy(dtype=float)
    r = other['rho'].to_numpy(dtype=float)
    ax.scatter(d + rng.uniform(-jitter_um, jitter_um, len(d)), r, s=14, color='0.55',
               alpha=0.45, lw=0, label='channel')
    centers = np.unique(d)
    med = np.array([np.median(r[d == c]) for c in centers])
    q1 = np.array([np.percentile(r[d == c], 25) for c in centers])
    q3 = np.array([np.percentile(r[d == c], 75) for c in centers])
    ax.fill_between(centers, q1, q3, color=EXTENT_COLOR, alpha=0.2, lw=0,
                    label='interquartile range')
    ax.plot(centers, med, '-o', color=EXTENT_COLOR, lw=2, ms=5, label='median')
    ax.axhline(rho_threshold, color=THRESHOLD_COLOR, lw=2, ls='--',
               label=f'ρ threshold = {rho_threshold:.2f}')
    ax.axhline(0, color='0.7', lw=0.8)
    ax.set_ylim(-1, 1)
    ax.set_xlim(0, d.max() + pitch if len(d) else pitch)
    ax.set_xlabel('Distance to nearest GA channel (µm)', fontsize=13)
    ax.set_ylabel(f'{ccs.method_name(method)} ρ with GA cluster response', fontsize=13)
    ax.set_title('Correlation vs distance', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, frameon=False, loc='lower left')


def plot_distributions(sessions, channels, *, rho_threshold, extent_bin_width_um=None,
                       split_probe_end=False, rho_bin_width=0.05,
                       normalize_channel_hist=True, jitter_um=8.0, seed=0,
                       method='spearman'):
    pitch = _pitch(channels)
    fig, axes = plt.subplots(1, 3, figsize=(21, 6.5),
                             gridspec_kw={'width_ratios': [1, 1, 1.3], 'wspace': 0.28})
    plot_extent_hist(axes[0], sessions, extent_bin_width_um or pitch, split_probe_end)
    plot_channel_rho_hist(axes[1], channels, rho_threshold, rho_bin_width,
                          normalize_channel_hist, method)
    plot_distance_scatter(axes[2], channels, rho_threshold, pitch, jitter_um,
                          np.random.default_rng(seed), method)
    for ax in axes:
        ax.tick_params(labelsize=11)
        ax.spines[['top', 'right']].set_visible(False)
    return fig


def main():
    session_ids = None       # None = every session in EStimShapeTrials; or a list
    start_session_id = COMPARISON_START_SESSION_ID          # same range as the
    exclude_session_ids = COMPARISON_EXCLUDE_SESSION_IDS    # estim comparison plots
    rho_threshold = 0.5      # ρ threshold : channels with ρ >= ρ threshold count as part of the cluster
    n_misses_to_stop = 2     # channels in a row below ρ threshold that end the walk
    method = 'spearman'      # 'spearman' or 'pearson'
    vector_type = 'ga_mean_response'
    extent_bin_width_um = 130   # extent histogram bin width (µm); None = probe pitch
    split_probe_end = False  # colour sessions that reach the probe end separately
    rho_bin_width = 0.05     # ρ histogram bin width (middle panel)
    normalize_channel_hist = True  # middle panel: each group sums to 1 (else counts)
    jitter_um = 8.0          # horizontal jitter on the scatter (distances are discrete)
    show_plots = True
    output_root = "/home/connorlab/Documents/plots/cluster_corr_extent_distributions"

    sids = select_sessions(session_ids, start_session_id, exclude_session_ids)
    sessions, channels, skipped = build_tables(
        sids, rho_threshold=rho_threshold, n_misses_to_stop=n_misses_to_stop,
        method=method, vector_type=vector_type)
    if sessions.empty:
        raise RuntimeError(f"No sessions with GA cluster data out of {len(sids)}")

    n_single = int((sessions['n_ga_channels'] < 2).sum())
    print(f"\n{len(sessions)} sessions used, {len(skipped)} skipped; "
          f"median extent = {sessions['extent_total_um'].median():.0f} µm "
          f"(up {sessions['extent_up_um'].median():.0f}, "
          f"down {sessions['extent_down_um'].median():.0f}); "
          f"{int(sessions['reaches_probe_end'].sum())} reach the probe end; "
          f"{n_single} with a single GA channel (no average GA ρ)")

    fig = plot_distributions(sessions, channels, rho_threshold=rho_threshold,
                             extent_bin_width_um=extent_bin_width_um,
                             split_probe_end=split_probe_end,
                             rho_bin_width=rho_bin_width,
                             normalize_channel_hist=normalize_channel_hist,
                             jitter_um=jitter_um, method=method)

    out_dir = os.path.join(output_root, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump({'session_ids': sids, 'start_session_id': start_session_id,
                   'exclude_session_ids': list(exclude_session_ids or []),
                   'rho_threshold': rho_threshold,
                   'n_misses_to_stop': n_misses_to_stop, 'method': method,
                   'vector_type': vector_type,
                   'extent_bin_width_um': extent_bin_width_um,
                   'split_probe_end': split_probe_end,
                   'rho_bin_width': rho_bin_width,
                   'normalize_channel_hist': normalize_channel_hist,
                   'jitter_um': jitter_um, 'skipped_sessions': skipped}, f, indent=2)
    sessions.to_csv(os.path.join(out_dir, "sessions.csv"), index=False)
    channels.to_csv(os.path.join(out_dir, "channels.csv"), index=False)
    for ext in ('png', 'svg'):
        fig.savefig(os.path.join(out_dir, f"cluster_corr_extent_distributions.{ext}"),
                    dpi=200, bbox_inches='tight')
    print(f"Saved to {out_dir}")
    if show_plots:
        plt.show()


if __name__ == "__main__":
    main()

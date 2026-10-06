"""
One figure per estim channel set in a session, showing how far response similarity
spreads from the stimulated site — the correlation half-distance (cluster size).

Left: the probe, top -> bottom (like the correlation columns in preference_cluster),
each channel coloured by the Spearman ρ between its GA response vector
(ga_mean_response) and the AVERAGE response of the estim channels (each estim
channel z-scored across stimuli before averaging, so one high-rate channel doesn't
dominate). One column no matter how many estim / GA cluster channels.
Estim channels are outlined with a square; GA cluster channels are stars.

Right: the data behind the correlation half-distance (exactly what
plot_current_spread_vs_tuning / cluster_size_distributions use): ρ for every
estim channel -> other channel pair vs their distance along the probe, the binned
(median) profile, its near-field and far-field (baseline) levels, and dotted lines
to the half point (d_half, half_level).

Specs in a session that stimulate the same channels share one figure.
"""

import os
import sys
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.channel_data_loaders import ClusterChannelLoader
from src.analysis.channel_metric_plot import (
    StimVectorCorrelation, default_cmap_norm, format_single_column_axis,
    plot_metric_column)
from src.analysis.nafc.group_analysis import plot_current_spread_vs_tuning as cs
from src.analysis.nafc.group_analysis.compute_estim_neighbor_scores import (
    channel_to_str, prepare_session_metrics)
from src.cluster.cluster_isolation_score import fetch_active_estim_channels_by_spec
from src.cluster.probe_mapping import DBCChannelMapper


def average_estim_response(response_matrix, estim_strs):
    """{stim_id: mean z-scored response across the estim channels}. Each channel is
    z-scored over its own stimuli first; a stim is averaged over whichever estim
    channels have it."""
    per_stim = {}
    for ch in estim_strs:
        vec = response_matrix.get(ch)
        if not vec:
            continue
        vals = np.array(list(vec.values()), dtype=float)
        mu, sd = np.nanmean(vals), np.nanstd(vals)
        if not np.isfinite(sd) or sd == 0:
            continue
        for stim, v in vec.items():
            if np.isfinite(v):
                per_stim.setdefault(stim, []).append((v - mu) / sd)
    return {stim: float(np.mean(vs)) for stim, vs in per_stim.items()}


def _estim_channel_sets(session_id, estim_spec_id=None):
    """[(spec_ids, estim Channel list)] — specs grouped by identical channel sets."""
    by_spec = fetch_active_estim_channels_by_spec(session_id)
    if estim_spec_id is not None:
        by_spec = {estim_spec_id: by_spec.get(estim_spec_id, [])}
    groups = {}
    for spec_id, chans in sorted(by_spec.items()):
        if chans:
            groups.setdefault(frozenset(chans), []).append(spec_id)
    return [(spec_ids, sorted(chans, key=lambda c: c.name))
            for chans, spec_ids in groups.items()]


def _plot_probe_column(ax, rho_by_ch, channel_strs, cluster_channels, estim_strs):
    cmap, norm = default_cmap_norm()
    ref = plot_metric_column(ax, rho_by_ch, channel_strs, cluster_channels,
                             cmap=cmap, norm=norm, show_yticks=True)
    format_single_column_axis(ax)
    for row_idx, ch in enumerate(channel_strs):
        if ch in estim_strs:
            ax.scatter(0, len(channel_strs) - row_idx, marker='s', s=300,
                       facecolors='none', edgecolors='black', linewidths=1.8,
                       zorder=20)
    ax.set_title('ρ vs avg estim\nresponse', fontsize=11, fontweight='bold')
    return ref


def _plot_spread(ax, dists, rhos, prof, pitch):
    ax.scatter(dists, rhos, s=12, color='0.6', alpha=0.5, lw=0,
               label='estim → channel pair')
    if prof is None:
        ax.text(0.5, 0.5, 'half-distance undefined\n(too few points or no decay)',
                transform=ax.transAxes, ha='center', va='center', color='tab:red')
    else:
        ax.plot(prof['centers'], prof['profile'], '-o', color='tab:blue', ms=4,
                label=f'binned {cs.DEFAULT_BIN_AGG} ({pitch:.0f} µm bins)')
        ax.axhline(prof['near_level'], color='tab:green', lw=1, ls='--',
                   label=f"near-field = {prof['near_level']:.2f}")
        ax.axhline(prof['baseline'], color='tab:purple', lw=1, ls='--',
                   label=f"far-field baseline = {prof['baseline']:.2f}")
        d, h = prof['d_half'], prof['half_level']
        x_lo, y_lo = ax.get_xlim()[0], ax.get_ylim()[0]
        ax.plot([x_lo, d], [h, h], ':', color='k', lw=1.5)
        ax.plot([d, d], [y_lo, h], ':', color='k', lw=1.5,
                label=f'half point: {d:.0f} µm (ρ = {h:.2f})')
        ax.plot(d, h, 'o', color='k', ms=6, zorder=10)
        ax.set_xlim(left=x_lo)
        ax.set_ylim(bottom=y_lo)
    ax.set_xlabel('Distance along probe from each estim channel (µm)\n'
                  '(pairs pooled over all estim channels)')
    ax.set_ylabel('Spearman ρ (GA response)')
    ax.set_title('Correlation vs distance', fontsize=11, fontweight='bold')
    # headroom above the data so the top-right legend doesn't sit on the curve
    y_lo, y_hi = ax.get_ylim()
    ax.set_ylim(y_lo, y_hi + 0.3 * (y_hi - y_lo))
    ax.legend(frameon=False, fontsize=8, loc='upper right')
    ax.spines[['top', 'right']].set_visible(False)


def plot_estim_correlation_spread(session_id, estim_spec_id=None, save_dir=None):
    """One figure per distinct estim channel set in the session (or just
    estim_spec_id's). Returns {tuple(spec_ids): half-distance µm or None}."""
    metrics, channels_with_data, coords = prepare_session_metrics(session_id)
    if metrics is None:
        return {}
    corr_metric = next((m for m in metrics if m.name == cs.CORR_METRIC_NAME), None)
    if corr_metric is None:
        print(f"{session_id}: no '{cs.CORR_METRIC_NAME}' metric")
        return {}
    response_matrix = corr_metric._matrix
    pitch = cs._probe_pitch(coords)
    channel_strs = [channel_to_str(c) for c in DBCChannelMapper("A").channels_top_to_bottom]
    cluster_channels = ClusterChannelLoader(
        session_id, Connection("allen_data_repository")).load()

    sets = _estim_channel_sets(session_id, estim_spec_id)
    if not sets:
        print(f"{session_id}: no estim specs with active channels")
        return {}

    results = {}
    for spec_ids, estim_channels in sets:
        estim_strs = {channel_to_str(c) for c in estim_channels}
        target = average_estim_response(response_matrix, estim_strs)
        rho_by_ch = StimVectorCorrelation(response_matrix, target,
                                          method='spearman').compute()

        dists, rhos = cs.pooled_distance_rho_pairs(
            corr_metric, estim_channels, channels_with_data, coords)
        prof = cs.half_distance_profile(dists, rhos, pitch=pitch)
        results[tuple(spec_ids)] = prof['d_half'] if prof else None

        fig = plt.figure(figsize=(12, 10))
        gs = GridSpec(1, 2, width_ratios=[1, 4], wspace=0.35, figure=fig)
        ax_col, ax_spread = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
        ref = _plot_probe_column(ax_col, rho_by_ch, channel_strs, cluster_channels,
                                 estim_strs)
        _plot_spread(ax_spread, dists, rhos, prof, pitch)
        if ref is not None:
            cbar = fig.colorbar(ref, ax=ax_col, orientation='horizontal',
                                pad=0.04, fraction=0.04)
            cbar.set_label('Spearman ρ')
        ax_col.legend(handles=[
            Line2D([0], [0], marker='s', color='w', markerfacecolor='none',
                   markeredgecolor='black', markersize=12, markeredgewidth=1.8,
                   label='Estim channel'),
            Line2D([0], [0], marker='*', color='w', markerfacecolor='lightcoral',
                   markeredgecolor='black', markersize=14, label='GA cluster channel'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgray',
                   markeredgecolor='gray', markersize=9, label='No data'),
        ], loc='upper center', bbox_to_anchor=(0.5, -0.12), fontsize=8, frameon=False)

        spec_label = ', '.join(str(s) for s in spec_ids)
        d_txt = f"{prof['d_half']:.0f} µm" if prof else 'undefined'
        fig.suptitle(f"{session_id} — estim spec{'s' if len(spec_ids) > 1 else ''} "
                     f"{spec_label} | estim channels: {', '.join(sorted(estim_strs))}\n"
                     f"correlation half-distance = {d_txt}",
                     fontsize=12, fontweight='bold')
        print(f"{session_id} specs [{spec_label}] estim {sorted(estim_strs)}: "
              f"half-distance = {d_txt}")
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            out = os.path.join(save_dir, f"estim_corr_spread_specs_"
                                         f"{'-'.join(str(s) for s in spec_ids)}.png")
            fig.savefig(out, dpi=200, bbox_inches='tight')
            print(f"Saved {out}")
        plt.show()
    return results


def main():
    session_id = "260402_0"
    plot_estim_correlation_spread(
        session_id,
        estim_spec_id=None,  # None -> one figure per distinct estim channel set
        save_dir=f"/home/connorlab/Documents/plots/{session_id}/estim_corr_spread")


if __name__ == "__main__":
    main()

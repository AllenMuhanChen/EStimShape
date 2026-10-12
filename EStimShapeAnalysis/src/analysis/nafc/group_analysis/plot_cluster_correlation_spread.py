"""
One session's GA cluster correlation spread: how far along the probe channels keep
responding like the GA cluster, measured with a fixed (hard) cutoff on ρ.

Reference: the GA cluster channels (ClusterInfo, latest gen). Each channel's GA
response vector (ga_mean_response) is correlated (Spearman) with the AVERAGE response
of the GA channels (each z-scored across stimuli first, so one high-rate channel
doesn't dominate). A GA channel is compared with the average of the OTHER GA channels
(leave-one-out), so it isn't correlated with itself.

Cutoff: a fixed ρ threshold (default 0.5, the conventional "strong correlation" boundary). A
channel with ρ >= ρ threshold counts as part of the cluster. ρ threshold is the same for every session,
so it is not relative to a session's own min/max correlation. (A p-value cutoff was
rejected: with 100+ stimuli almost every channel is weakly but significantly
correlated, since nearby V4 columns share tuning.)

Contiguous extent, done separately up and down the probe:
  start at the top-most (bottom-most) GA channel and walk up (down) one channel at a
  time; channels without data are skipped. The walk stops after N_MISSES_TO_STOP
  channels in a row below ρ threshold; the edge of the cluster is the last channel >= ρ threshold before
  them. If the walk reaches the end of the probe without stopping, that side is
  flagged as reaching the probe end (the true extent may be larger).
  extent_up / extent_down = distance (µm) from the GA channels' edge to that side's
  boundary channel. Total extent = distance between the upper and lower boundary
  channels (centre to centre), so it includes the span of the GA channels themselves.

Left: the probe, top -> bottom, each channel coloured by ρ; GA channels are stars,
channels >= ρ threshold have a thick outline. Right: ρ by probe position (same rows), with the
ρ threshold line, the walk's stopping channels (x) and the extent shaded.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.channel_data_loaders import (ChannelResponseVectorLoader,
                                               ClusterChannelLoader)
from src.analysis.channel_metric_plot import (default_cmap_norm,
                                              format_single_column_axis,
                                              plot_metric_column)
from src.analysis.nafc.group_analysis.compute_estim_neighbor_scores import channel_to_str
from src.cluster.probe_mapping import DBCChannelMapper
from src.startup.apply_session_context import apply_session_context


# ---------------------------------------------------------------- correlation

def zscore_average(response_matrix, channel_strs):
    """{stim_id: mean z-scored response across channel_strs}. Each channel is z-scored
    over its own stimuli first; a stim is averaged over whichever channels have it."""
    per_stim = {}
    for ch in channel_strs:
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


def correlate(vec, target, method='spearman', min_common=3):
    """(ρ, n) between a channel's {stim: response} and target {stim: value} over their
    common stimuli. ρ is NaN when there are too few stimuli or no variance."""
    common = [s for s in vec if s in target
              and np.isfinite(vec[s]) and np.isfinite(target[s])]
    n = len(common)
    if n < max(3, min_common):
        return np.nan, n
    a = np.array([vec[s] for s in common], dtype=float)
    b = np.array([target[s] for s in common], dtype=float)
    if np.std(a) == 0 or np.std(b) == 0:
        return np.nan, n
    corr = stats.spearmanr if method == 'spearman' else stats.pearsonr
    return float(corr(a, b)[0]), n


def ga_reference_rhos(response_matrix, ga_strs, method='spearman'):
    """{channel: (ρ, n)} vs the average GA response. GA channels are compared with the
    average of the other GA channels (leave-one-out); with a single GA channel it has
    no reference and gets ρ = NaN."""
    ga_strs = [g for g in ga_strs if g in response_matrix]
    target_all = zscore_average(response_matrix, ga_strs)
    out = {}
    for ch, vec in response_matrix.items():
        if ch in ga_strs:
            others = [g for g in ga_strs if g != ch]
            if not others:
                out[ch] = (np.nan, 0)
                continue
            out[ch] = correlate(vec, zscore_average(response_matrix, others), method)
        else:
            out[ch] = correlate(vec, target_all, method)
    return out


# ---------------------------------------------------------------- contiguous extent

def _walk(indices, above, has_data, n_misses_to_stop):
    """Walk channel indices in order. Returns (last index >= ρ threshold or None,
    [indices of the misses that stopped the walk], reached_probe_end)."""
    last_sig, misses = None, []
    for i in indices:
        if not has_data[i]:
            continue
        if above[i]:
            last_sig, misses = i, []
        else:
            misses.append(i)
            if len(misses) >= n_misses_to_stop:
                return last_sig, misses, False
    return last_sig, misses, True


def contiguous_extent(channel_strs, positions_um, rho_n, ga_strs, *, rho_threshold=0.5,
                      n_misses_to_stop=2):
    """Bidirectional contiguous extent of ρ >= rho_threshold around the GA channels.

    channel_strs: probe channels top -> bottom; positions_um: their position along the
    probe (µm); rho_n: {channel: (ρ, n)}. Returns a dict (see module docstring), or None
    if no GA channel is on the probe."""
    pos = np.asarray(positions_um, dtype=float)
    ga_idx = [i for i, ch in enumerate(channel_strs) if ch in ga_strs]
    if not ga_idx:
        return None
    top, bottom = min(ga_idx), max(ga_idx)

    rho = np.array([rho_n.get(ch, (np.nan, 0))[0] for ch in channel_strs], dtype=float)
    n = np.array([rho_n.get(ch, (np.nan, 0))[1] for ch in channel_strs], dtype=int)
    has_data = np.isfinite(rho)
    above = has_data & (rho >= rho_threshold)

    up_sig, up_miss, up_end = _walk(range(top - 1, -1, -1), above, has_data,
                                    n_misses_to_stop)
    dn_sig, dn_miss, dn_end = _walk(range(bottom + 1, len(channel_strs)), above,
                                    has_data, n_misses_to_stop)
    up_edge = top if up_sig is None else up_sig
    dn_edge = bottom if dn_sig is None else dn_sig
    return {
        'rho': rho, 'n': n, 'rho_threshold': rho_threshold, 'above': above,
        'has_data': has_data, 'ga_top': top, 'ga_bottom': bottom,
        'up_edge': up_edge, 'down_edge': dn_edge,
        'up_stop': up_miss, 'down_stop': dn_miss,
        'up_reached_end': up_end, 'down_reached_end': dn_end,
        'extent_up_um': float(abs(pos[top] - pos[up_edge])),
        'extent_down_um': float(abs(pos[dn_edge] - pos[bottom])),
        'extent_total_um': float(abs(pos[up_edge] - pos[dn_edge])),
        'ga_span_um': float(abs(pos[top] - pos[bottom])),
    }


# ---------------------------------------------------------------- plotting

def _row_y(n_rows, idx):
    """plot_metric_column's row position (top channel at the top)."""
    return n_rows - idx


def _plot_probe_column(ax, ext, channel_strs, ga_strs):
    cmap, norm = default_cmap_norm()
    rho_by_ch = {ch: ext['rho'][i] for i, ch in enumerate(channel_strs)}
    ref = plot_metric_column(ax, rho_by_ch, channel_strs, set(ga_strs),
                             cmap=cmap, norm=norm, show_yticks=True)
    format_single_column_axis(ax)
    rows = len(channel_strs)
    for i in np.where(ext['above'])[0]:
        ax.scatter(0, _row_y(rows, i), marker='o', s=320, facecolors='none',
                   edgecolors='black', linewidths=2.0, zorder=20)
    ax.axhspan(_row_y(rows, ext['down_edge']) - 0.5, _row_y(rows, ext['up_edge']) + 0.5,
               color='gold', alpha=0.25, zorder=0, lw=0)
    ax.set_title('ρ vs GA\nresponse', fontsize=13, fontweight='bold')
    return ref


def _plot_profile(ax, ext, channel_strs, n_misses_to_stop):
    rows = len(channel_strs)
    y = np.array([_row_y(rows, i) for i in range(rows)])
    rho, thr = ext['rho'], ext['rho_threshold']
    ok = ext['has_data']
    sig = ext['above']

    ax.axhspan(_row_y(rows, ext['down_edge']) - 0.5, _row_y(rows, ext['up_edge']) + 0.5,
               color='gold', alpha=0.25, lw=0, zorder=0)
    ax.axvline(0, color='0.7', lw=0.8, zorder=1)
    ax.axvline(thr, color='tab:red', lw=2, ls='--', zorder=2)
    ax.plot(np.where(ok, rho, np.nan), y, color='0.5', lw=1, zorder=3)
    ax.scatter(rho[ok & ~sig], y[ok & ~sig], s=60, facecolor='white',
               edgecolor='0.3', lw=1.2, zorder=4)
    ax.scatter(rho[sig], y[sig], s=60, color='black', zorder=5)
    is_ga = np.array([ch in ext.get('ga_strs', ()) for ch in channel_strs])
    if is_ga.any():
        ax.scatter(rho[is_ga & ok], y[is_ga & ok], marker='*', s=260,
                   color='lightcoral', edgecolor='black', lw=0.8, zorder=6)
    for i in ext['up_stop'] + ext['down_stop']:
        ax.scatter(rho[i], y[i], marker='x', s=140, color='tab:red', lw=2.5, zorder=7)

    # one double-headed arrow on the right edge spanning the whole extent
    # (upper boundary channel -> lower boundary channel), ticked at both ends
    x_arrow, tick = 1.03, 0.025
    y_up, y_dn = _row_y(rows, ext['up_edge']), _row_y(rows, ext['down_edge'])
    if y_up != y_dn:
        ax.annotate('', xy=(x_arrow, y_up), xytext=(x_arrow, y_dn),
                    arrowprops=dict(arrowstyle='<|-|>', color='darkgoldenrod', lw=2,
                                    shrinkA=0, shrinkB=0, mutation_scale=15),
                    annotation_clip=False)
    for y_end in (y_up, y_dn):
        ax.plot([x_arrow - tick, x_arrow + tick], [y_end, y_end], color='black',
                lw=1.5, clip_on=False)
    ax.text(x_arrow + 0.04, 0.5 * (y_up + y_dn), f"{ext['extent_total_um']:.0f} µm",
            va='center', ha='left', fontsize=11, color='darkgoldenrod', clip_on=False)

    ax.set_xlim(-1, 1)
    ax.tick_params(axis='y', left=False, labelleft=False)
    ax.set_xlabel('Spearman ρ with GA cluster response', fontsize=13)
    ax.tick_params(labelsize=11)
    ax.set_title('Correlation along the probe', fontsize=13, fontweight='bold')
    ax.legend(handles=[
        Line2D([0], [0], color='tab:red', ls='--', lw=2,
               label=f"ρ threshold = {thr:.2f}"),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='black',
               markersize=9, label='ρ ≥ ρ threshold'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='white',
               markeredgecolor='0.3', markersize=9, label='ρ < ρ threshold'),
        Line2D([0], [0], marker='*', color='w', markerfacecolor='lightcoral',
               markeredgecolor='black', markersize=15,
               label='GA channel (vs other GA channels)'),
        Line2D([0], [0], marker='x', color='tab:red', lw=0, markersize=10,
               markeredgewidth=2.5,
               label=f'walk stops ({n_misses_to_stop} misses in a row)'),
        Patch(facecolor='gold', alpha=0.25, label='contiguous extent'),
    ], loc='upper center', bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=11,
       frameon=False)
    ax.spines[['top', 'right']].set_visible(False)


def plot_extent_figure(session_id, ext, channel_strs, ga_strs, *,
                       n_misses_to_stop, fig=None):
    """fig: a matplotlib Figure to draw into (e.g. matplotlib.figure.Figure for the
    GA explorer); None makes a pyplot figure."""
    ext = dict(ext, ga_strs=set(ga_strs))
    if fig is None:
        fig = plt.figure(figsize=(13, 11))
    # colorbar gets its own row so both panels keep the same height (rows line up)
    gs = GridSpec(2, 2, width_ratios=[1, 4], height_ratios=[40, 1], wspace=0.25,
                  hspace=0.08, figure=fig)
    ax_col = fig.add_subplot(gs[0, 0])
    ax_prof = fig.add_subplot(gs[0, 1], sharey=ax_col)
    ref = _plot_probe_column(ax_col, ext, channel_strs, ga_strs)
    _plot_profile(ax_prof, ext, channel_strs, n_misses_to_stop)
    if ref is not None:
        cbar = fig.colorbar(ref, cax=fig.add_subplot(gs[1, 0]),
                            orientation='horizontal')
        cbar.set_label('Spearman ρ', fontsize=11)
    fig.suptitle(f"{session_id}: GA cluster extent = {ext['extent_total_um']:.0f} µm "
                 f"at ρ threshold = {ext['rho_threshold']:.2f}",
                 fontsize=15, fontweight='bold')
    return fig


# ---------------------------------------------------------------- session driver

def load_session_rhos(session_id, *, method='spearman',
                      vector_type='ga_mean_response', switch_context=True):
    """Everything the extent needs for one session: (rho_n, channel_strs, positions_um,
    ga_strs). rho_n = {channel: (ρ vs GA response, n stimuli)}; channel_strs /
    positions_um are the probe channels top -> bottom and their positions (µm);
    ga_strs = GA cluster channels that have response data. Raises RuntimeError if the
    session has no response vectors or no GA channel with data. switch_context=False
    when the caller (e.g. the GA explorer) has already switched to this session."""
    if switch_context:
        apply_session_context(session_id)
    repo_conn = Connection("allen_data_repository")
    response_matrix = ChannelResponseVectorLoader(session_id, repo_conn,
                                                  vector_type=vector_type).load()
    if not response_matrix:
        raise RuntimeError(f"{session_id}: no ChannelResponseVectors ({vector_type})")
    ga_strs = sorted(ClusterChannelLoader(session_id, repo_conn).load())
    ga_with_data = [g for g in ga_strs if g in response_matrix]
    if not ga_with_data:
        raise RuntimeError(f"{session_id}: no GA cluster channels with response data "
                           f"(ClusterInfo channels: {ga_strs})")

    mapper = DBCChannelMapper("A")
    channel_strs = [channel_to_str(c) for c in mapper.channels_top_to_bottom]
    positions_um = [float(mapper.get_coordinates(c)[1])
                    for c in mapper.channels_top_to_bottom]
    rho_n = ga_reference_rhos(response_matrix, ga_with_data, method=method)
    return rho_n, channel_strs, positions_um, ga_with_data


def plot_cluster_correlation_spread(session_id, *, rho_threshold=0.5,
                                    n_misses_to_stop=2, method='spearman',
                                    vector_type='ga_mean_response', output_root=None):
    """Compute and plot one session's contiguous extent. Returns the extent dict."""
    rho_n, channel_strs, positions_um, ga_with_data = load_session_rhos(
        session_id, method=method, vector_type=vector_type)
    ext = contiguous_extent(channel_strs, positions_um, rho_n, ga_with_data,
                            rho_threshold=rho_threshold,
                            n_misses_to_stop=n_misses_to_stop)
    print_extent(session_id, ext, ga_with_data)
    fig = plot_extent_figure(session_id, ext, channel_strs, ga_with_data,
                             n_misses_to_stop=n_misses_to_stop)

    if output_root:
        out_dir = os.path.join(output_root, datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "config.json"), "w") as f:
            json.dump({'session_id': session_id, 'rho_threshold': rho_threshold,
                       'n_misses_to_stop': n_misses_to_stop,
                       'method': method, 'vector_type': vector_type,
                       'ga_channels': ga_with_data,
                       'extent_total_um': ext['extent_total_um'],
                       'extent_up_um': ext['extent_up_um'],
                       'extent_down_um': ext['extent_down_um'],
                       'up_reached_probe_end': ext['up_reached_end'],
                       'down_reached_probe_end': ext['down_reached_end']},
                      f, indent=2)
        for ext_name in ('png', 'svg'):
            fig.savefig(os.path.join(out_dir, f"cluster_corr_spread.{ext_name}"),
                        dpi=200, bbox_inches='tight')
        print(f"Saved to {out_dir}")
    plt.show()
    return ext


def print_extent(session_id, ext, ga_strs):
    ok = ext['has_data']
    print(f"{session_id}: GA channels {ga_strs}; ρ threshold = {ext['rho_threshold']:.2f}; "
          f"{int(ext['above'].sum())}/{int(ok.sum())} channels with ρ ≥ ρ threshold")
    print(f"  extent up = {ext['extent_up_um']:.0f} µm"
          f"{' (probe end)' if ext['up_reached_end'] else ''}, "
          f"down = {ext['extent_down_um']:.0f} µm"
          f"{' (probe end)' if ext['down_reached_end'] else ''}, "
          f"total = {ext['extent_total_um']:.0f} µm "
          f"(GA channels span {ext['ga_span_um']:.0f} µm)")


def main():
    session_id = "260702_0"
    rho_threshold = 0.5      # ρ threshold : channels with ρ >= ρ threshold count as part of the cluster
    n_misses_to_stop = 2     # channels in a row below ρ threshold that end the walk
    method = 'spearman'      # 'spearman' or 'pearson'
    output_root = f"/home/connorlab/Documents/plots/{session_id}/cluster_corr_spread"

    plot_cluster_correlation_spread(session_id, rho_threshold=rho_threshold,
                                    n_misses_to_stop=n_misses_to_stop, method=method,
                                    output_root=output_root)


if __name__ == "__main__":
    main()

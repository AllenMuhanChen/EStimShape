"""
Correlation helpers for probe columns that compare every channel with a GROUP of
channels (the GA cluster, or the estim channels) rather than with one channel.

Same method as plot_cluster_correlation_spread (GA-cluster correlation extent):
  - the group's reference response is the average of its channels' responses, each
    channel z-scored across stimuli first so one high-rate channel doesn't dominate;
  - a channel that is itself in the group is compared with the average of the OTHER
    group channels (leave-one-out), so it isn't correlated with itself;
  - the contiguous extent walks up and down the probe from the group's edges and
    stops after n_misses_to_stop channels in a row below a fixed ρ threshold.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


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


def group_reference_rhos(response_matrix, group_strs, method='spearman',
                         leave_one_out=True):
    """{channel: ρ} vs the group's average response. With leave_one_out, a group
    channel is compared with the average of the other group channels (a group of one
    then has no reference for its own channel: ρ = NaN)."""
    group_strs = [g for g in group_strs if g in response_matrix]
    target_all = zscore_average(response_matrix, group_strs)
    out = {}
    for ch, vec in response_matrix.items():
        if leave_one_out and ch in group_strs:
            others = [g for g in group_strs if g != ch]
            out[ch] = (correlate(vec, zscore_average(response_matrix, others), method)[0]
                       if others else np.nan)
        else:
            out[ch] = correlate(vec, target_all, method)[0]
    return out


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


def contiguous_extent(channel_strs, positions_um, rho_by_ch, group_strs, *,
                      rho_threshold=0.5, n_misses_to_stop=2):
    """Bidirectional contiguous extent of ρ >= rho_threshold around the group channels.

    channel_strs: probe channels top -> bottom; positions_um: their position along the
    probe (µm); rho_by_ch: {channel: ρ}. Returns None if no group channel is on the
    probe, else a dict with the row indices of the edges (up_edge / down_edge), the
    extents in µm (extent_up_um, extent_down_um, extent_total_um) and whether each side
    reached the probe end (the true extent may then be larger)."""
    pos = np.asarray(positions_um, dtype=float)
    idx = [i for i, ch in enumerate(channel_strs) if ch in group_strs]
    if not idx:
        return None
    top, bottom = min(idx), max(idx)
    rho = np.array([rho_by_ch.get(ch, np.nan) for ch in channel_strs], dtype=float)
    has_data = np.isfinite(rho)
    above = has_data & (rho >= rho_threshold)

    up_sig, up_miss, up_end = _walk(range(top - 1, -1, -1), above, has_data,
                                    n_misses_to_stop)
    dn_sig, dn_miss, dn_end = _walk(range(bottom + 1, len(channel_strs)), above,
                                    has_data, n_misses_to_stop)
    up_edge = top if up_sig is None else up_sig
    dn_edge = bottom if dn_sig is None else dn_sig
    return {
        'rho_threshold': rho_threshold, 'above': above,
        'group_top': top, 'group_bottom': bottom,
        'up_edge': up_edge, 'down_edge': dn_edge,
        'up_stop': up_miss, 'down_stop': dn_miss,
        'up_reached_end': up_end, 'down_reached_end': dn_end,
        'extent_up_um': float(abs(pos[top] - pos[up_edge])),
        'extent_down_um': float(abs(pos[dn_edge] - pos[bottom])),
        'extent_total_um': float(abs(pos[up_edge] - pos[dn_edge])),
    }

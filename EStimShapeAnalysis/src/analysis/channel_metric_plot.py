"""
channel_metric_plot.py
----------------------
Shared plotting primitives for "channel × metric" dot-column plots.

Both `delta_variant_correlation.py` and `preference_cluster.py` render the same
visual primitive: channels arranged top → bottom on the y-axis, with one or
more columns of dots coloured by a per-channel scalar metric on RdBu_r /
TwoSlopeNorm centred at zero.  Cluster channels are drawn as ★, others as ●;
missing data falls back to gray.

The metric calculation differs between callers (z-scored Spearman vs raw
Spearman vs preference indices) and so does the column layout — but the
per-column rendering is identical, so it lives here.

Public surface:
    CHANNEL_ORDER                  – top → bottom DBC channel order
    build_channel_strings(label)   – list of "<label>-<num>" channel strings
    default_cmap_norm()            – (RdBu_r, TwoSlopeNorm(-1, 0, 1))
    plot_metric_column(...)        – render one column of channel dots
    format_single_column_axis(ax)  – x-limits / ticks / centre line / grid
    cluster_marker_legend_handles(include_no_data=True)
                                   – Line2D handles for the standard legend
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D


# Channel order top → bottom (matches DBCChannelMapper)
CHANNEL_ORDER: List[int] = [
    7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
    27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17,
]


def build_channel_strings(headstage_label: str = "A") -> List[str]:
    """Return the channel-string list ordered top → bottom."""
    return [f"{headstage_label}-{num:03d}" for num in CHANNEL_ORDER]


def default_cmap_norm():
    """Default RdBu_r colormap and TwoSlopeNorm centred at zero (vmin/vmax = ±1)."""
    return plt.cm.RdBu_r, TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(np.isnan(value))
    except TypeError:
        return False


def plot_metric_column(
        ax,
        metric_data: Dict[str, float],
        channel_strings: List[str],
        cluster_channels: Set[str],
        *,
        cmap=None,
        norm=None,
        self_channel: Optional[str] = None,
        x_position: float = 0.0,
        show_yticks: bool = False,
):
    """
    Render a single column of per-channel metric values.

    Args:
        ax:               Target matplotlib axis.
        metric_data:      ``{channel_string: scalar}``.  Missing keys or NaN
                          values are drawn as gray "no data" markers.
        channel_strings:  Ordered list of channel names (top → bottom).
        cluster_channels: Channel names rendered as ★ (others as ●).
        cmap, norm:       Colour mapping; defaults to RdBu_r centred at zero.
        self_channel:     If given, the marker for this channel gets a thick
                          edge — used to flag the cluster channel against
                          itself in correlation columns.
        x_position:       X coordinate for all markers in this column.  Use
                          offsets when stacking multiple metrics on a shared
                          axis (e.g. one frequency per x-position).
        show_yticks:      Render channel names as y-tick labels on this axis.

    Returns:
        The last value-coloured scatter Artist drawn (suitable as a colorbar
        mappable), or None if no value markers were drawn.
    """
    if cmap is None or norm is None:
        cmap_default, norm_default = default_cmap_norm()
        cmap = cmap if cmap is not None else cmap_default
        norm = norm if norm is not None else norm_default

    scatter_ref = None
    for row_idx, channel_str in enumerate(channel_strings):
        y_pos = len(channel_strings) - row_idx  # top → bottom
        is_cluster = channel_str in cluster_channels
        is_self = (self_channel is not None) and (channel_str == self_channel)
        value = metric_data.get(channel_str, np.nan)

        if not _is_missing(value):
            scatter_ref = ax.scatter(
                x_position, y_pos,
                c=value, s=200 if is_cluster else 100,
                marker='*' if is_cluster else 'o',
                cmap=cmap, norm=norm,
                edgecolors='black',
                linewidths=2.0 if is_self else 0.5,
                alpha=0.9 if is_cluster else 0.8,
                zorder=10 if is_cluster else 1,
            )
        else:
            ax.scatter(
                x_position, y_pos,
                c='lightgray', s=120 if is_cluster else 50,
                marker='*' if is_cluster else 'o',
                edgecolors='black' if is_cluster else 'gray',
                linewidths=0.5,
                alpha=0.7 if is_cluster else 0.5,
                zorder=10 if is_cluster else 1,
            )

    ax.set_ylim(0.5, len(channel_strings) + 0.5)
    if show_yticks:
        ax.set_yticks(range(1, len(channel_strings) + 1))
        ax.set_yticklabels(channel_strings[::-1], fontsize=8)
        ax.set_ylabel('Channel (Top → Bottom)', fontsize=10)

    return scatter_ref


def format_single_column_axis(ax) -> None:
    """Apply the standard x-axis formatting for a single-metric column."""
    ax.set_xlim(-0.5, 0.5)
    ax.set_xticks([])
    ax.axvline(0, color='black', linewidth=0.5, alpha=0.3)
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')


def cluster_marker_legend_handles(include_no_data: bool = True) -> List[Line2D]:
    """Standard legend handles describing the cluster / other / no-data markers."""
    handles = [
        Line2D([0], [0], marker='*', color='w', markerfacecolor='lightcoral',
               markeredgecolor='black', markersize=14, markeredgewidth=2,
               label='Cluster channel', linestyle='None'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='lightcoral',
               markeredgecolor='black', markersize=10, markeredgewidth=0.5,
               label='Other channel', linestyle='None'),
    ]
    if include_no_data:
        handles.append(
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgray',
                   markeredgecolor='gray', markersize=10, markeredgewidth=0.5,
                   label='No data', linestyle='None')
        )
    return handles

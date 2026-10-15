"""
Draw ColumnBlocks as one probe figure: channels top -> bottom on a shared y axis, one
narrow column of coloured dots per quantity, GA channels as stars.

Layout is fixed (no tight_layout), so columns, group labels, colorbars and legends
never overlap however many columns are on:
    top     column titles, and a bracketed group label over multi-column blocks
    middle  the columns, with a small gap between blocks
    bottom  one strip with the colour scales in use and the marker legend
"""

from __future__ import annotations

import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from src.analysis.channel_metric_plot import (default_cmap_norm, format_single_column_axis,
                                              plot_metric_column)
from src.analysis.probe_analysis.probe_columns import (CATEGORICAL, CYCLIC, DIVERGING,
                                                       SEQUENTIAL)
from src.analysis.probe_analysis.probe_data import PROBE_PITCH_UM

ESTIM_COLOR = '#8B8000'          # hatch + label for estim channels (pub_single_column)
EXTENT_COLOR = 'gold'

COL_W = 1.05                     # inches per column
GAP_W = 0.35                     # inches between blocks
LEFT_IN, RIGHT_IN = 1.5, 0.9     # y labels / 'EStim' labels
TOP_IN_ONE, TOP_IN_GROUPS = 1.3, 1.75
BOTTOM_IN = 1.9                  # colorbar + legend strip (side by side)
SLOT_MIN_IN = 2.8                # narrower than this per item -> stack them
SLOT_H_IN = 1.25                 # height per item when stacked
MIN_WIDTH_IN = 6.0
PROBE_H_IN = 9.5


def _scale_cmap_norm(block):
    if block.scale == CYCLIC:
        return 'hsv', Normalize(vmin=-1.0, vmax=1.0)
    if block.scale == CATEGORICAL:
        cmap = ListedColormap([block.category_colors[c] for c in block.categories])
        return cmap, BoundaryNorm(np.arange(-0.5, len(block.categories) + 0.5, 1.0), cmap.N)
    if block.scale == SEQUENTIAL:
        return 'magma', Normalize(vmin=0.0, vmax=block.vmax)
    return default_cmap_norm()


def _y_labels(channel_strs, mode):
    depth = [f"{i * PROBE_PITCH_UM / 1000:.2f}" for i in range(len(channel_strs))]
    if mode == 'depth':
        return depth, 'Depth along probe (mm)'
    if mode == 'both':
        return [f"{c}  {d}" for c, d in zip(channel_strs, depth)], 'Channel, depth (mm)'
    return list(channel_strs), 'Channel (top → bottom)'


def draw_probe_figure(blocks, channel_strs, ga_channels, *, estim_channels=(),
                      title="", y_labels='channel', font_size=11, figure=None):
    """Draw the blocks; returns the matplotlib Figure.

    figure: None makes a non-pyplot Figure (for the explorer); pass a callable such as
    ``lambda **kw: plt.figure(**kw)`` to get one plt.show() can display."""
    if figure is None:
        from matplotlib.figure import Figure
        figure = Figure
    n_cols = sum(len(b.subs) for b in blocks)
    has_groups = any(b.label for b in blocks)
    top_in = TOP_IN_GROUPS if has_groups else TOP_IN_ONE
    width = LEFT_IN + RIGHT_IN + n_cols * COL_W + GAP_W * max(0, len(blocks) - 1)
    width = max(width, MIN_WIDTH_IN)
    # Colour scales + marker legend side by side when there's room, else stacked.
    n_slots = len({b.scale for b in blocks}) + 1
    stacked = (width - 0.6) / n_slots < SLOT_MIN_IN
    bottom_in = (0.4 + SLOT_H_IN * n_slots) if stacked else BOTTOM_IN
    height = top_in + PROBE_H_IN + bottom_in
    fig = figure(figsize=(width, height))

    n = len(channel_strs)
    rows_y = {ch: n - i for i, ch in enumerate(channel_strs)}   # plot_metric_column's y
    estim_channels = [e for e in estim_channels if e in rows_y]
    ga_channels = set(ga_channels)

    # column x positions (inches from the left), then figure fractions
    x = LEFT_IN + (width - LEFT_IN - RIGHT_IN - n_cols * COL_W
                   - GAP_W * max(0, len(blocks) - 1)) / 2
    bottom, top = bottom_in / height, 1 - top_in / height
    tick_labels, y_title = _y_labels(channel_strs, y_labels)
    first_ax, last_ax = None, None
    used_scales = {}
    any_ring = any_extent = False

    for b_idx, block in enumerate(blocks):
        if b_idx:
            x += GAP_W
        cmap, norm = _scale_cmap_norm(block)
        block_axes = []
        for sub in block.subs:
            ax = fig.add_axes([x / width, bottom, COL_W * 0.9 / width, top - bottom],
                              sharey=first_ax)
            x += COL_W
            plot_metric_column(ax, sub.data, channel_strs, ga_channels, cmap=cmap,
                               norm=norm, self_channel=sub.self_channel)
            format_single_column_axis(ax)
            ax.set_title(sub.title, fontsize=font_size, fontweight='bold')
            ax.tick_params(axis='y', labelleft=first_ax is None, labelsize=font_size - 2)
            if first_ax is None:
                first_ax = ax
                ax.set_yticks(range(1, n + 1))
                ax.set_yticklabels(tick_labels[::-1])
                ax.set_ylabel(y_title, fontsize=font_size + 1)
            for e in estim_channels:
                ax.axhspan(rows_y[e] - 0.5, rows_y[e] + 0.5, facecolor='none',
                           hatch='////', edgecolor=ESTIM_COLOR, linewidth=0.4, zorder=0)
            for ch in block.ringed:
                if ch in rows_y:
                    ax.scatter(0, rows_y[ch], marker='o', s=330, facecolors='none',
                               edgecolors='black', linewidths=2.0, zorder=20)
                    any_ring = True
            if block.extent_rows is not None:
                up, down = block.extent_rows
                ax.axhspan(n - down - 0.5, n - up + 0.5, color=EXTENT_COLOR, alpha=0.3,
                           lw=0, zorder=0)
                any_extent = True
            block_axes.append(ax)
            last_ax = ax
        used_scales.setdefault(block.scale, (block, cmap, norm))
        if block.label:
            _group_label(fig, block_axes, block.label, font_size)

    if last_ax is not None:
        for e in estim_channels:
            last_ax.text(1.06, rows_y[e], 'EStim', transform=last_ax.get_yaxis_transform(),
                         ha='left', va='center', fontsize=font_size, color=ESTIM_COLOR,
                         clip_on=False)
    if first_ax is not None:
        first_ax.set_ylim(0.5, n + 0.5)

    _bottom_strip(fig, used_scales, width, height, font_size, stacked=stacked,
                  has_ga=bool(ga_channels), has_estim=bool(estim_channels),
                  has_ring=any_ring, has_extent=any_extent)
    if title:
        fig.suptitle(title, fontsize=font_size + 4, fontweight='bold',
                     y=1 - 0.15 / height, va='top')
    return fig


def _group_label(fig, axes, label, font_size):
    """Bracket over the block's columns with the group label above it."""
    x0, x1 = axes[0].get_position().x0, axes[-1].get_position().x1
    y = axes[0].get_position().y1
    fig_h = fig.get_size_inches()[1]
    y_line = y + 0.75 / fig_h
    fig.add_artist(Line2D([x0, x1], [y_line, y_line], transform=fig.transFigure,
                          color='#333333', lw=1.2))
    for xe in (x0, x1):
        fig.add_artist(Line2D([xe, xe], [y_line, y_line - 0.08 / fig_h],
                              transform=fig.transFigure, color='#333333', lw=1.2))
    fig.text((x0 + x1) / 2, y_line + 0.05 / fig_h, label, ha='center', va='bottom',
             fontsize=font_size + 1, fontweight='bold', color='#333333')


def _bottom_strip(fig, used_scales, width, height, font_size, *, stacked, has_ga,
                  has_estim, has_ring, has_extent):
    """Colour scales in use, then the marker legend: left to right, or top to bottom
    when the figure is narrow."""
    items = [s for s in (DIVERGING, SEQUENTIAL, CYCLIC, CATEGORICAL) if s in used_scales]
    slots = len(items) + 1

    def slot(i):
        """(x0, y0, w, h) in inches of slot i."""
        if stacked:
            return 0.5, 0.2 + SLOT_H_IN * (slots - 1 - i), width - 1.0, SLOT_H_IN
        slot_w = (width - 0.6) / slots
        return 0.3 + i * slot_w, 0.1, slot_w, BOTTOM_IN - 0.2

    for i, scale in enumerate(items):
        block, cmap, norm = used_scales[scale]
        sx, sy, sw, sh = slot(i)
        x0, w = (sx + 0.25) / width, (min(sw, 4.5) - 0.5) / width
        if scale == CATEGORICAL:
            ax = fig.add_axes([x0, sy / height, w, sh / height])
            ax.axis('off')
            ax.legend(handles=[Line2D([0], [0], marker='o', color='w', label=c,
                                      markerfacecolor=block.category_colors[c],
                                      markeredgecolor='black', markersize=10)
                               for c in block.categories],
                      title='Preferred colour', ncol=2, loc='center', frameon=False,
                      fontsize=font_size - 1, title_fontsize=font_size)
            continue
        from matplotlib.cm import ScalarMappable
        cax = fig.add_axes([x0, (sy + sh - 0.45) / height, w, 0.18 / height])
        cbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                            orientation='horizontal')
        cbar.ax.tick_params(labelsize=font_size - 1)
        if scale == DIVERGING:
            cbar.set_label("index or ρ, −1 to +1\nred: 3D / isochromatic / high freq / "
                           "positive ρ", fontsize=font_size)
        elif scale == CYCLIC:
            cbar.set_ticks([-1.0, -0.5, 0.0, 0.5, 1.0])
            cbar.set_ticklabels(['0°', '45°', '90°', '135°', '180°'])
            cbar.set_label(block.scale_label, fontsize=font_size)
        else:
            cbar.set_label(block.scale_label, fontsize=font_size)

    handles = []
    if has_ga:
        handles.append(Line2D([0], [0], marker='*', color='w', markerfacecolor='lightcoral',
                              markeredgecolor='black', markersize=15, label='GA channel'))
    handles += [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='lightcoral',
               markeredgecolor='black', markersize=10, label='Other channel'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgray',
               markeredgecolor='gray', markersize=10, label='No data'),
    ]
    if has_estim:
        handles.append(Patch(facecolor='none', edgecolor=ESTIM_COLOR, hatch='////',
                             label='EStim channel'))
    if has_ring:
        handles.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='none',
                              markeredgecolor='black', markeredgewidth=2, markersize=14,
                              label='ρ ≥ ρ threshold'))
    if has_extent:
        handles.append(Patch(facecolor=EXTENT_COLOR, alpha=0.3, label='GA extent'))
    sx, sy, sw, sh = slot(len(items))
    lax = fig.add_axes([sx / width, sy / height, sw / width, sh / height])
    lax.axis('off')
    lax.legend(handles=handles, loc='center', ncol=2 if len(handles) > 3 else 1,
               frameon=False, fontsize=font_size - 1)

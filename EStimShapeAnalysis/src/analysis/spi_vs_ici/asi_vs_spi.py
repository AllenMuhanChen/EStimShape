"""Population plot: Solid Preference Index (SPI) vs. Alignment Suppression Index (ASI).

x-axis = solid_preference_index  (SolidPreferenceIndices; 3D-preferring is positive)
y-axis = alignment_suppression_index  (MixedGaborAlignmentIndices; aligned color
         suppresses the luminance response when positive)

Points are colored by the same significance/direction categories used in the
SPI-vs-ICI plots (significant 2D = green, non-significant = gray, significant 3D
= red), and per-category regression lines are drawn.

Reuses the spi_vs_ici machinery:
  - channel selection modes (`selection_mode`): 'double_filter', 'raw_significant',
    'cluster', 'mapped_channel' -- mirrors spi_vs_ici.py.
  - the caller-supplied `bin_edges` feature (from spi_vs_ici_preferred_freq.py) --
    here it bins the *luminance frequency* so each bin is emitted as its own plot.

The hypothesis (aligned color contrast obscures luminance contrast for
3D/luminance-preferring cells) predicts significant-3D cells sitting at positive
ASI -- i.e. a positive SPI->ASI relationship, strongest at the higher frequencies.
"""
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from clat.util.connection import Connection
from src.analysis.spi_vs_ici.spi_vs_ici_preferred_freq import (
    REGRESSION_CATEGORIES,
    categorize_points,
    plot_category_regressions,
    print_category_regressions,
    linregress_with_spi_cap,
)


# ---------------------------------------------------------------------------
# Data loading (mirrors spi_vs_ici.py's selection_mode machinery, but joins
# MixedGaborAlignmentIndices instead of IsochromaticPreferenceIndices).
# ---------------------------------------------------------------------------
def _selection_clause(alias, selection_mode):
    """Return (join_sql, where_sql) applying a selection_mode's channel filter to
    a query whose primary table is aliased `alias`. Mirrors the JOIN/WHERE logic
    in spi_vs_ici.py so ASI is drawn from exactly the same channel populations."""
    if selection_mode == 'double_filter':
        joins = (f"JOIN GoodChannels g ON {alias}.session_id = g.session_id AND {alias}.unit_name = g.channel "
                 f"JOIN ChannelFiltering c ON {alias}.session_id = c.session_id AND {alias}.unit_name = c.channel")
        where = "c.is_good = TRUE"
    elif selection_mode == 'raw_significant':
        joins = ""
        where = f"{alias}.unit_name NOT LIKE '%Unit%'"
    elif selection_mode == 'cluster':
        joins = (f"JOIN Experiments e ON {alias}.session_id = e.session_id "
                 f"JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND {alias}.unit_name = c.channel")
        where = "1 = 1"
    elif selection_mode == 'mapped_channel':
        joins = (f"JOIN Experiments e ON {alias}.session_id = e.session_id "
                 f"JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND {alias}.unit_name = c.channel "
                 f"JOIN ReceptiveFieldInfo r ON r.session_id = {alias}.session_id AND r.channel = {alias}.unit_name")
        where = "1 = 1"
    else:
        raise ValueError(f"Unknown selection_mode: {selection_mode}. "
                         f"Use 'double_filter', 'raw_significant', 'cluster', or 'mapped_channel'")
    return joins, where


def load_asi_spi_data(selection_mode='cluster'):
    """Load (merged_df, data_description) joining SolidPreferenceIndices and
    MixedGaborAlignmentIndices for the requested selection mode.

    merged_df columns: session_id, unit_name, solid_preference_index, p_value,
    luminance_frequency, alignment_suppression_index, color_pair.
    """
    conn = Connection("allen_data_repository")

    solid_joins, solid_where = _selection_clause('s', selection_mode)
    asi_joins, asi_where = _selection_clause('i', selection_mode)

    # raw_significant restricts the solid side to significant units (matches
    # spi_vs_ici.load_raw_significant_channels_data).
    if selection_mode == 'raw_significant':
        solid_where = solid_where + " AND s.p_value < 0.05"

    solid_query = f"""
        SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
        FROM SolidPreferenceIndices s
        {solid_joins}
        WHERE {solid_where}
    """
    asi_query = f"""
        SELECT i.session_id, i.unit_name, i.luminance_frequency,
               i.alignment_suppression_index, i.color_pair
        FROM MixedGaborAlignmentIndices i
        {asi_joins}
        WHERE {asi_where}
    """

    conn.execute(solid_query)
    solid_df = pd.DataFrame(conn.fetch_all(),
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])
    solid_df = solid_df.drop_duplicates(['session_id', 'unit_name'])

    conn.execute(asi_query)
    asi_df = pd.DataFrame(conn.fetch_all(),
                          columns=['session_id', 'unit_name', 'luminance_frequency',
                                   'alignment_suppression_index', 'color_pair'])
    asi_df = asi_df.drop_duplicates(['session_id', 'unit_name', 'luminance_frequency'])

    merged_df = pd.merge(solid_df, asi_df, on=['session_id', 'unit_name'], how='inner')

    descriptions = {
        'double_filter': "Validated Channels (GoodChannels AND is_good=TRUE)",
        'raw_significant': "Raw Significant Channels (solid-pref p < 0.05, no spike sorting)",
        'cluster': "Cluster Channels (ClusterInfo)",
        'mapped_channel': "Mapped Channels (cluster channels also in ReceptiveFieldInfo)",
    }
    return merged_df, descriptions[selection_mode]


# ---------------------------------------------------------------------------
# Frequency binning (the bin_edges feature from spi_vs_ici_preferred_freq.py,
# applied to luminance frequency).
# ---------------------------------------------------------------------------
def compute_frequency_bins(data, bin_edges=None):
    """Group rows by luminance frequency for per-plot output.

    Args:
        data: DataFrame with a 'luminance_frequency' column.
        bin_edges: Optional explicit edges, e.g. [0, 1.5, np.inf] -> bins
            [0, 1.5] and [1.5, inf]. When None, each distinct luminance frequency
            is its own bin.

    Returns:
        (data_with_bins, bin_specs) where bin_specs is a list of
        (bin_key, label, mask) tuples ready to iterate for plotting.
    """
    data = data.copy()
    bin_specs = []
    if bin_edges is not None:
        data['freq_bin'] = pd.cut(data['luminance_frequency'], bins=list(bin_edges),
                                  include_lowest=True)
        for interval in data['freq_bin'].cat.categories:
            mask = data['freq_bin'] == interval
            label = f"luminance freq [{interval.left:g}, {interval.right:g}] cyc/deg"
            bin_specs.append((interval, label, mask))
    else:
        for freq in sorted(data['luminance_frequency'].unique()):
            mask = data['luminance_frequency'] == freq
            label = f"luminance freq {freq:g} cyc/deg"
            bin_specs.append((freq, label, mask))
    return data, bin_specs


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def _format_asi_axes(ax):
    """Reference lines, limits, labels, and hypothesis quadrant labels for an
    SPI (x) vs ASI (y) plot. Both indices are bounded [-1, 1]."""
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_xlabel('Solid Preference Index  (3D-preferring →)', fontsize=13)
    ax.set_ylabel('Alignment Suppression Index  (aligned color suppresses →)', fontsize=13)

    # Upper-right is the hypothesis-consistent quadrant.
    ax.text(0.55, 0.92, '3D-pref &\naligned suppresses\n(hypothesis)', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral', alpha=0.5), fontsize=9)
    ax.text(-0.55, 0.92, '2D-pref &\naligned suppresses', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.4), fontsize=9)
    ax.text(0.55, -0.92, '3D-pref &\naligned enhances', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.5), fontsize=9)
    ax.text(-0.55, -0.92, '2D-pref &\naligned enhances', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.5), fontsize=9)


def plot_asi_vs_spi(data, title, save_path=None, spi_regression_max=None):
    """Scatter of SPI (x) vs ASI (y), points colored by significance category,
    with per-category regression lines. Returns the per-category regression stats."""
    if data.empty:
        print(f"No data for: {title}")
        return None

    x = data['solid_preference_index'].values.astype(float)
    y = data['alignment_suppression_index'].values.astype(float)
    p_values = data['p_value'].values
    categories = categorize_points(x, p_values)

    plt.figure(figsize=(11, 9))
    ax = plt.gca()

    # Points colored by category; significant points are opaque with a dark edge,
    # non-significant points are faint.
    for label, color in REGRESSION_CATEGORIES:
        mask = categories == label
        if not mask.any():
            continue
        if label == 'Non-sig.':
            alpha_val, edge_color, lw = 0.2, 'gray', 0.3
        else:
            alpha_val, edge_color, lw = 0.75, 'black', 0.5
        ax.scatter(x[mask], y[mask], s=80, color=color, alpha=alpha_val,
                   edgecolors=edge_color, linewidths=lw)

    # Per-category regression lines (sig 2D / non-sig / sig 3D), each over its own
    # x-range, optionally excluding high-SPI points from the fit.
    category_results = plot_category_regressions(ax, x, y, p_values,
                                                 spi_regression_max=spi_regression_max)

    # Overall regression across all points (for the stats box).
    _, _, r_all, p_all, r2_all, x_all = linregress_with_spi_cap(x, y, spi_regression_max)

    _format_asi_axes(ax)

    n_sig = int(np.sum((pd.notna(p_values)) & (p_values < 0.05)))
    ax.set_title(f'{title}\n(n={len(data)} points, {n_sig} solid-pref significant)', fontsize=14)

    stats_text = (f'Overall\nR² = {r2_all:.3f}\nr = {r_all:.3f}\n'
                  f'p = {p_all:.3f}\nn = {len(x_all)}')
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, verticalalignment='top',
            fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles=handles, labels=labels, loc='upper left',
                  bbox_to_anchor=(1.02, 1), title='Category (color = point color)')

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")

    return category_results


def create_asi_vs_spi_plots(selection_mode='cluster', spi_regression_max=None,
                            bin_edges=None, save_dir=None):
    """Top-level entry point.

    Args:
        selection_mode: Channel selection ('double_filter', 'raw_significant',
            'cluster', 'mapped_channel') -- same machinery as spi_vs_ici.py.
        spi_regression_max: If not None, points with SPI above this value are
            excluded from every regression (still plotted).
        bin_edges: Optional luminance-frequency bin edges, e.g. [0, 1.5, np.inf].
            Each bin is emitted as its own plot. When None, one plot per distinct
            luminance frequency (plus an all-frequencies-pooled plot in both cases).
        save_dir: Directory to save PNGs. If None, plots are only displayed.
    """
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)

    merged_df, data_description = load_asi_spi_data(selection_mode)
    if merged_df.empty:
        print(f"No matching data found for {data_description}")
        return None

    print(f"Data source: {data_description}")
    print(f"Total units: {merged_df['unit_name'].nunique()}, "
          f"data points (unit x luminance freq): {len(merged_df)}")
    if spi_regression_max is not None:
        print(f"Excluding SPI > {spi_regression_max} from all regressions")

    # 1) All luminance frequencies pooled.
    print("\n" + "=" * 60)
    print("Plot: SPI vs ASI -- all luminance frequencies pooled")
    print("=" * 60)
    save_path = os.path.join(save_dir, "asi_vs_spi_all.png") if save_dir else None
    results = plot_asi_vs_spi(merged_df, f"SPI vs ASI -- all luminance frequencies\n{data_description}",
                              save_path, spi_regression_max)
    if results:
        print_category_regressions(results)

    # 2) Per luminance-frequency bin (bin_edges) or per distinct frequency.
    binned_df, bin_specs = compute_frequency_bins(merged_df, bin_edges)
    for i, (bin_key, label, mask) in enumerate(bin_specs):
        bin_data = binned_df[mask]
        print("\n" + "=" * 60)
        print(f"Plot: SPI vs ASI -- {label}")
        print("=" * 60)
        if bin_data.empty:
            print("  (no data in this bin)")
            continue
        fname = f"asi_vs_spi_bin{i + 1}.png"
        save_path = os.path.join(save_dir, fname) if save_dir else None
        results = plot_asi_vs_spi(bin_data, f"SPI vs ASI -- {label}\n{data_description}",
                                  save_path, spi_regression_max)
        if results:
            print(f"  {label}: n={len(bin_data)}")
            print_category_regressions(results)

    plt.show()
    return merged_df


if __name__ == "__main__":
    # Channel selection mode -- same options as spi_vs_ici.py:
    #   'double_filter'   - GoodChannels AND ChannelFiltering
    #   'raw_significant' - raw significant channels (solid-pref p < 0.05)
    #   'cluster'         - cluster channels via ClusterInfo
    #   'mapped_channel'  - cluster channels also in ReceptiveFieldInfo
    selection_mode = 'mapped_channel'

    # Exclude points with Solid Preference Index above this from every regression
    # (still plotted). None uses all points.
    spi_regression_max = None

    # Luminance-frequency bins -> one plot per bin. None = one plot per distinct
    # luminance frequency. Example: [0, 1.5, np.inf] for low vs high.
    bin_edges = None
    # bin_edges = [0, 1.5, np.inf]

    create_asi_vs_spi_plots(
        selection_mode=selection_mode,
        spi_regression_max=spi_regression_max,
        bin_edges=[0, 1.5, 2.5, 8.0, np.inf],
        save_dir="/home/connorlab/Documents/plots/spi_vs_asi_mapped_channel",
    )

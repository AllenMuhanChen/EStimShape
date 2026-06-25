"""
spi_vs_ici_orientation.py
-------------------------
Orientation-tuning views built on the spi_vs_ici machinery.

Two deliverables:

1. ``plot_orientation_strong_spi_vs_ici`` - the usual Solid-vs-Isochromatic
   preference scatter (by frequency), but restricted to the cells *and*
   frequencies where orientation tuning is strong: a (cell, frequency) pair is
   kept only if its orientation tuning depth (``max_minus_min`` from
   ``PreferredOrientations``) is at least ``threshold`` (default 0.7 = 70%) of
   that cell's peak tuning depth across all of its frequencies. This mirrors the
   "strong frequencies" idea in spi_vs_ici_preferred_freq.parse_strong_frequencies,
   applied to orientation tuning instead of raw response.

2. ``plot_rf_size_vs_orientation_tuning`` - scatter with x = cycles per RF
   (stimulus frequency x RF diameter = ``frequency * 2 * rf_radius``) and
   y = orientation tuning (``max_minus_min``), one point per (cell, frequency).

Both reuse channel selection (``load_data_for_selection_mode``) and the RF radius
merge (``merge_receptive_field_radius``) from the sibling modules. Not every
session has orientation data; a missing/empty ``PreferredOrientations`` table is
handled gracefully (empty DataFrame, a printed warning, no crash).
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from clat.util.connection import Connection
from src.analysis.spi_vs_ici.spi_vs_ici import (
    load_data_for_selection_mode,
    calculate_regression_with_spi_cap,
)
from src.analysis.spi_vs_ici.spi_vs_ici_preferred_freq import merge_receptive_field_radius


# Spatial frequencies used across the spi_vs_ici plots
TARGET_FREQUENCIES = [0.5, 1.0, 2.0, 4.0]


def load_preferred_orientations():
    """Load all rows from ``PreferredOrientations``.

    Returns a DataFrame with columns ``session_id, unit_name, frequency,
    preferred_orientation, max_response, max_minus_min``. Returns an empty
    DataFrame (with those columns) if the table is missing or empty.
    """
    columns = ['session_id', 'unit_name', 'frequency',
               'preferred_orientation', 'max_response', 'max_minus_min']
    conn = Connection("allen_data_repository")
    try:
        conn.execute(
            """SELECT session_id, unit_name, frequency,
                      preferred_orientation, max_response, max_minus_min
               FROM PreferredOrientations"""
        )
        rows = conn.fetch_all()
    except Exception as e:
        print(f"Could not load PreferredOrientations (table may not exist): {e}")
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        print("PreferredOrientations is empty - no orientation data available")
        return df

    df['frequency'] = pd.to_numeric(df['frequency'], errors='coerce')
    df['max_minus_min'] = pd.to_numeric(df['max_minus_min'], errors='coerce')
    df['preferred_orientation'] = pd.to_numeric(df['preferred_orientation'], errors='coerce')
    df = df.dropna(subset=['frequency', 'max_minus_min'])
    return df


def add_orientation_tuning_strength(orient_df, threshold=0.7):
    """Flag (cell, frequency) rows whose orientation tuning is >= threshold of the
    cell's peak tuning depth across its frequencies.

    Adds ``cell_max_tuning`` and a boolean ``orientation_strong`` column.
    """
    orient_df = orient_df.copy()
    orient_df['cell_max_tuning'] = (
        orient_df.groupby(['session_id', 'unit_name'])['max_minus_min'].transform('max')
    )
    # cell_max_tuning <= 0 means no positive tuning anywhere; treat as not strong.
    orient_df['orientation_strong'] = (
        (orient_df['cell_max_tuning'] > 0)
        & (orient_df['max_minus_min'] >= threshold * orient_df['cell_max_tuning'])
    )
    return orient_df


# ---------------------------------------------------------------------------
# Deliverable 1: SPI vs ICI restricted to orientation-strong cells/frequencies
# ---------------------------------------------------------------------------

def _subplot_grid(n):
    if n <= 2:
        return 1, max(n, 1)
    if n <= 4:
        return 2, 2
    return 2, (n + 1) // 2


def load_orientation_strong_data(selection_mode='mapped_channel', threshold=0.7):
    """Build the orientation-strong SPI/ICI dataset.

    Loads the SPI/ICI rows for the selected channels, merges orientation tuning
    from ``PreferredOrientations``, and keeps only the (cell, frequency) pairs
    whose tuning depth is >= ``threshold`` of that cell's peak tuning depth.

    Returns ``(strong_df, data_description)``; ``strong_df`` is ``None`` if no
    data / no orientation data / nothing passes the threshold.
    """
    merged_df, data_description = load_data_for_selection_mode(selection_mode)
    if merged_df.empty:
        print(f"No matching data found for {data_description}")
        return None, data_description

    orient_df = load_preferred_orientations()
    if orient_df.empty:
        print("No orientation data available - cannot build orientation-strong plot")
        return None, data_description

    orient_df = add_orientation_tuning_strength(orient_df, threshold)

    # Merge orientation strength onto the SPI/ICI rows (per session/unit/frequency)
    merged_df = merged_df.copy()
    merged_df['frequency'] = pd.to_numeric(merged_df['frequency'], errors='coerce')
    merged = merged_df.merge(
        orient_df[['session_id', 'unit_name', 'frequency',
                   'max_minus_min', 'cell_max_tuning', 'orientation_strong']],
        on=['session_id', 'unit_name', 'frequency'], how='inner'
    )

    # Keep only orientation-strong (cell, frequency) pairs
    strong = merged[merged['orientation_strong']].copy()
    strong = strong[strong['frequency'].isin(TARGET_FREQUENCIES)]

    if strong.empty:
        print(f"No orientation-strong data at >= {threshold:.0%} of peak tuning "
              f"for {data_description}")
        return None, data_description

    n_cells = strong[['session_id', 'unit_name']].drop_duplicates().shape[0]
    print(f"Orientation-strong SPI vs ICI ({data_description}): "
          f"{len(strong)} (cell, freq) points across {n_cells} cells, "
          f"threshold >= {threshold:.0%} of peak tuning")
    return strong, data_description





def plot_orientation_strong_spi_vs_ici(selection_mode='mapped_channel', threshold=0.7,
                                       regression_method='ols', spi_regression_max=None,
                                       save_path=None):
    """SPI vs ICI by frequency, restricted to orientation-strong (cell, frequency) pairs.

    Args:
        selection_mode: Channel selection ('double_filter', 'raw_significant',
            'cluster', 'mapped_channel') - same options as spi_vs_ici.py.
        threshold: Keep (cell, frequency) where orientation tuning depth is at
            least this fraction of the cell's peak tuning depth (default 0.7).
        regression_method: 'ols' or 'theil-sen'.
        spi_regression_max: Exclude points with SPI above this from regressions.
        save_path: Optional path to save the figure.
    """
    strong, data_description = load_orientation_strong_data(selection_mode, threshold)
    if strong is None or strong.empty:
        return None

    frequencies = sorted(strong['frequency'].unique())
    nrows, ncols = _subplot_grid(len(frequencies))
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows), squeeze=False)
    axes = axes.flatten()
    fig.suptitle(
        f'Solid vs Isochromatic Preference - Orientation-Strong Cells/Frequencies\n'
        f'{data_description} (tuning >= {threshold:.0%} of peak, '
        f'{regression_method.upper()} regression)',
        fontsize=15)

    for ax_idx, frequency in enumerate(frequencies):
        ax = axes[ax_idx]
        freq_data = strong[strong['frequency'] == frequency]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} Hz (n=0)')
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-1.1, 1.1)
            continue

        x = freq_data['solid_preference_index'].values
        y = freq_data['isochromatic_preference_index'].values
        p_values = freq_data['p_value'].values

        slope, intercept, r_value, p_value, r_squared, x_reg = calculate_regression_with_spi_cap(
            x, y, regression_method, spi_regression_max)

        # Significant solid-preference points solid blue, others faded gray
        sig_mask = pd.notna(p_values) & (p_values < 0.05)
        ax.scatter(x[sig_mask], y[sig_mask], alpha=threshold, s=60, color='blue', label='sig.')
        ax.scatter(x[~sig_mask], y[~sig_mask], alpha=0.25, s=60, color='gray')

        if len(x_reg) > 1 and not np.isnan(slope):
            line_x = np.linspace(x_reg.min(), x_reg.max(), 100)
            ax.plot(line_x, slope * line_x + intercept, 'r-', linewidth=2, alpha=0.8)

        n_sig = int(np.sum(sig_mask))
        ax.set_title(f'{frequency} Hz (n={len(freq_data)}, {n_sig} sig.)')
        ax.set_xlabel('Solid Preference Index')
        ax.set_ylabel('Isochromatic Preference Index')
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)

        if len(x_reg) > 1:
            stats_text = f'R²={r_squared:.3f}\nr={r_value:.3f}\np={p_value:.3f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                    verticalalignment='top', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    for idx in range(len(frequencies), len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved orientation-strong SPI vs ICI plot: {save_path}")
    plt.show()

    return strong


def plot_orientation_strong_spi_vs_ici_combined(selection_mode='mapped_channel', threshold=0.7,
                                                regression_method='ols', spi_regression_max=None,
                                                save_path=None):
    """SPI vs ICI for orientation-strong cells/frequencies, pooled into a single
    scatter (NOT split by frequency).

    Every orientation-strong (cell, frequency) point is plotted on one axis,
    with a single regression over the pooled data.

    Args:
        selection_mode: Channel selection (same options as spi_vs_ici.py).
        threshold: Keep (cell, frequency) where orientation tuning depth is at
            least this fraction of the cell's peak tuning depth (default 0.7).
        regression_method: 'ols' or 'theil-sen'.
        spi_regression_max: Exclude points with SPI above this from the regression.
        save_path: Optional path to save the figure.
    """
    strong, data_description = load_orientation_strong_data(selection_mode, threshold)
    if strong is None or strong.empty:
        return None

    x = strong['solid_preference_index'].values
    y = strong['isochromatic_preference_index'].values
    p_values = strong['p_value'].values

    slope, intercept, r_value, p_value, r_squared, x_reg = calculate_regression_with_spi_cap(
        x, y, regression_method, spi_regression_max)

    n_cells = strong[['session_id', 'unit_name']].drop_duplicates().shape[0]

    plt.figure(figsize=(10, 8))

    # Significant solid-preference points solid blue, others faded gray
    sig_mask = pd.notna(p_values) & (p_values < 0.05)
    plt.scatter(x[sig_mask], y[sig_mask], alpha=threshold, s=60, color='blue',
                label=f'solid-pref sig. (n={int(sig_mask.sum())})')
    plt.scatter(x[~sig_mask], y[~sig_mask], alpha=0.25, s=60, color='gray',
                label=f'not sig. (n={int((~sig_mask).sum())})')

    if len(x_reg) > 1 and not np.isnan(slope):
        line_x = np.linspace(x_reg.min(), x_reg.max(), 100)
        plt.plot(line_x, slope * line_x + intercept, 'r-', linewidth=2, alpha=0.8,
                 label=f'{regression_method.upper()} fit (R²={r_squared:.3f})')

    plt.xlabel('Solid Preference Index')
    plt.ylabel('Isochromatic Preference Index')
    plt.title(
        f'Solid vs Isochromatic Preference - Orientation-Strong (pooled across frequencies)\n'
        f'{data_description} (tuning >= {threshold:.0%} of peak, '
        f'{len(strong)} points, {n_cells} cells)')
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3)
    plt.xlim(-1.1, 1.1)
    plt.ylim(-1.1, 1.1)
    plt.legend(loc='best')

    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {len(strong)}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved pooled orientation-strong SPI vs ICI plot: {save_path}")
    plt.show()

    return strong


# ---------------------------------------------------------------------------
# Deliverable 2: cycles-per-RF vs orientation tuning depth
#
# Mirrors plot_cycles_per_rf_vs_response in
# receptive_fields/rf_size_vs_preferred_freq.py: orientation tuning is
# z-scored per unit (across that unit's frequencies) and a binned mean +/- SEM
# trend line is overlaid on the scatter.
# ---------------------------------------------------------------------------

def _normalize_per_unit(values, method='zscore'):
    """Normalize a single unit's tuning values across its tested frequencies.

    'zscore' -> per-unit z-score, 'max' -> divide by the unit's max, 'none' -> raw.
    Returns None when normalization is undefined (zero variance / non-positive max).
    """
    values = np.asarray(values, dtype=float)
    if method == 'none':
        return values
    if method == 'max':
        peak = np.max(values)
        if not np.isfinite(peak) or peak <= 0:
            return None
        return values / peak
    if method == 'zscore':
        sd = np.std(values)
        if not np.isfinite(sd) or sd == 0:
            return None
        return (values - np.mean(values)) / sd
    raise ValueError(f"Unknown normalize: {method}. Use 'zscore', 'max', or 'none'")


def _compute_bin_edges(xb, n_bins, bin_edges):
    """Bin edges for the cycles-per-RF trend: explicit edges or n equal-width bins."""
    if bin_edges is not None:
        return np.asarray(bin_edges, dtype=float)
    return np.linspace(xb.min(), xb.max(), n_bins + 1)


def _binned_mean_sem(xb, yb, edges):
    """Mean +/- SEM of yb within each cycles-per-RF bin. Skips empty bins."""
    n_bin = len(edges) - 1
    idx = np.digitize(xb, edges) - 1
    centers, means, sems = [], [], []
    for b in range(n_bin):
        sel = (idx == b) if b < n_bin - 1 else (idx == b) | (xb == edges[-1])
        n = int(sel.sum())
        if n > 0:
            hi = edges[b + 1] if np.isfinite(edges[b + 1]) else xb[sel].max()
            centers.append(0.5 * (edges[b] + hi))
            means.append(yb[sel].mean())
            sems.append(yb[sel].std(ddof=1) / np.sqrt(n) if n > 1 else 0.0)
    return centers, means, sems


def expand_orientation_tuning(selection_mode='mapped_channel', normalize='zscore'):
    """Build a per-(unit, frequency) cycles-per-RF / orientation-tuning dataset.

    For each selected unit, orientation tuning depth (``max_minus_min``) is
    normalized across that unit's tested frequencies (per-unit z-score by
    default), and ``cycles_per_rf = frequency * 2 * rf_radius`` is computed.

    Returns ``(long_df, data_description)``; ``long_df`` is ``None`` if no data.
    Columns: session_id, unit_name, rf_radius, frequency, tuning, norm_tuning,
    cycles_per_rf.
    """
    base_df, data_description = load_data_for_selection_mode(selection_mode)
    if base_df.empty:
        print(f"No matching channels found for {data_description}")
        return None, data_description

    orient_df = load_preferred_orientations()
    if orient_df.empty:
        print("No orientation data available - cannot build RF-size vs tuning plot")
        return None, data_description

    # Restrict orientation data to the selected channels and attach RF radius
    selected = base_df[['session_id', 'unit_name']].drop_duplicates()
    orient_sel = orient_df.merge(selected, on=['session_id', 'unit_name'], how='inner')
    if orient_sel.empty:
        print(f"No orientation data for selected channels ({data_description})")
        return None, data_description

    orient_sel = merge_receptive_field_radius(orient_sel)

    # Per-unit normalization is over the unit's full orientation tuning profile
    # (all its frequencies), then we keep points with a valid RF radius to plot.
    records = []
    n_skipped_norm = 0
    for (session_id, unit_name), grp in orient_sel.groupby(['session_id', 'unit_name']):
        grp = grp.dropna(subset=['max_minus_min'])
        if grp.empty:
            continue
        norm = _normalize_per_unit(grp['max_minus_min'].values, normalize)
        if norm is None:
            n_skipped_norm += 1  # undefined normalization (e.g. zero variance)
            continue
        for (_, r), nv in zip(grp.iterrows(), norm):
            records.append({
                'session_id': session_id,
                'unit_name': unit_name,
                'rf_radius': r['rf_radius'],
                'frequency': r['frequency'],
                'tuning': r['max_minus_min'],
                'norm_tuning': nv,
                'cycles_per_rf': r['frequency'] * 2.0 * r['rf_radius'],
            })

    if n_skipped_norm > 0:
        print(f"Skipped {n_skipped_norm} unit(s) with undefined '{normalize}' "
              f"normalization (e.g. tuning identical across frequencies)")

    long_df = pd.DataFrame.from_records(records)
    if long_df.empty:
        print("No orientation tuning points available after normalization")
        return None, data_description

    # Keep only points with a valid RF radius (needed for cycles-per-RF)
    valid = long_df['rf_radius'].notna() & (long_df['rf_radius'] > 0)
    n_missing = int((~valid).sum())
    if n_missing > 0:
        print(f"WARNING: {n_missing} of {len(long_df)} (unit, frequency) points "
              f"lack a valid RF radius and are skipped.")
    long_df = long_df[valid].copy()
    if long_df.empty:
        print("No points with valid RF radius available for RF-size vs tuning plot")
        return None, data_description

    return long_df, data_description


def plot_rf_size_vs_orientation_tuning(selection_mode='mapped_channel', normalize='zscore',
                                       n_bins=8, bin_edges=None, xlim=None, save_path=None):
    """Cycles per RF (x) vs orientation tuning (y), with a binned mean +/- SEM trend.

    Copies plot_cycles_per_rf_vs_response: one point per (unit, frequency), the
    orientation tuning depth (max - min) z-scored per unit across its frequencies,
    points colored by stimulus frequency, and a black binned mean +/- SEM trend line.

    cycles per RF = stimulus frequency x RF diameter = ``frequency * 2 * rf_radius``.

    Args:
        selection_mode: Channel selection mode (same options as spi_vs_ici.py).
            'mapped_channel' is recommended since it requires RF info.
        normalize: Per-unit tuning normalization ('zscore', 'max', or 'none').
        n_bins: Number of equal-width cycles-per-RF bins for the trend line
            (used only when bin_edges is None).
        bin_edges: Optional explicit bin edges, e.g. [0, 2, 4, 8, np.inf].
        xlim: Optional (xmin, xmax) display crop (all points still used for the trend).
        save_path: Optional path to save the figure.
    """
    long_df, data_description = expand_orientation_tuning(selection_mode, normalize)
    if long_df is None or long_df.empty:
        return None

    y_col = 'tuning' if normalize == 'none' else 'norm_tuning'
    x = long_df['cycles_per_rf'].values
    y = long_df[y_col].values

    n_cells = long_df[['session_id', 'unit_name']].drop_duplicates().shape[0]
    print(f"RF-size vs orientation tuning ({data_description}, normalize='{normalize}'): "
          f"{len(long_df)} (unit, freq) points across {n_cells} units; "
          f"cycles_per_rf range [{np.nanmin(x):.3f}, {np.nanmax(x):.3f}]")

    fig, ax = plt.subplots(figsize=(9, 7))

    # Discrete color per stimulus frequency
    freqs = sorted(long_df['frequency'].unique())
    cmap = plt.cm.viridis
    for i, freq in enumerate(freqs):
        m = long_df['frequency'] == freq
        ax.scatter(long_df.loc[m, 'cycles_per_rf'], long_df.loc[m, y_col],
                   s=45, alpha=0.5, color=cmap(i / max(1, len(freqs) - 1)),
                   edgecolors='none', label=f'{freq:g} Hz')

    # Binned mean +/- SEM trend line
    finite = np.isfinite(x) & np.isfinite(y)
    xb, yb = x[finite], y[finite]
    if len(xb) >= 2 and xb.min() < xb.max():
        edges = _compute_bin_edges(xb, n_bins, bin_edges)
        centers, means, sems = _binned_mean_sem(xb, yb, edges)
        if centers:
            ax.errorbar(centers, means, yerr=sems, color='black', linewidth=2.5,
                        marker='o', capsize=3, zorder=5,
                        label=f'binned mean ± SEM (n={len(xb)})')

    if normalize == 'zscore':
        ax.axhline(0, color='gray', linestyle='--', alpha=0.5)

    if xlim is not None:
        ax.set_xlim(xlim)
    ax.set_xlabel('Cycles per RF (frequency × RF diameter)', fontsize=13)
    ax.set_ylabel(_tuning_label(normalize), fontsize=13)
    ax.set_title(f'Orientation tuning vs cycles per RF\n{data_description} '
                 f'(n={len(long_df)} unit×frequency points, {n_cells} units)', fontsize=13)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9, title='Stimulus frequency')
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved RF-size vs orientation tuning plot: {save_path}")
    plt.show()

    return long_df


def _tuning_label(normalize):
    return {
        'zscore': 'Orientation tuning (max − min, z-scored per unit)',
        'max': 'Orientation tuning (max − min, normalized to unit max)',
        'none': 'Orientation tuning (max − min response, spikes/s)',
    }.get(normalize, 'Orientation tuning (max − min)')


if __name__ == "__main__":
    # Channel selection mode (see spi_vs_ici.py for options). 'mapped_channel'
    # requires RF info, which is needed for the cycles-per-RF plot.
    selection_mode = 'mapped_channel'
    save_dir = None  # e.g. "/home/connorlab/Documents/plots"
    threshold = 0.75

    # Cycles-per-RF x-axis range for the orientation-tuning plot. Set to None to
    # auto-scale, or e.g. (0, 8) to crop the display (all points still feed the
    # binned trend). Matches the cycles_xlim option in rf_size_vs_preferred_freq.py.
    cycles_xlim = [0,10]  # e.g. (0, 8)

    def _path(name):
        return os.path.join(save_dir, name) if save_dir else None

    # 1) SPI vs ICI for orientation-strong cells/frequencies (tuning >= 70% of peak)
    plot_orientation_strong_spi_vs_ici(
        selection_mode=selection_mode, threshold=threshold,
        regression_method='ols', spi_regression_max=0.3,
        save_path=_path("orientation_strong_spi_vs_ici.png"))

    # 1b) Same data, pooled into a single scatter (not split by frequency)
    plot_orientation_strong_spi_vs_ici_combined(
        selection_mode=selection_mode, threshold=threshold,
        regression_method='ols', spi_regression_max=0.3,
        save_path=_path("orientation_strong_spi_vs_ici_combined.png"))

    # 2) Cycles per RF vs orientation tuning (max - min), z-scored per unit with
    #    a binned mean +/- SEM trend line.
    plot_rf_size_vs_orientation_tuning(
        selection_mode=selection_mode, normalize='zscore', n_bins=8,
        xlim=cycles_xlim,
        save_path=_path("rf_size_vs_orientation_tuning.png"),
        bin_edges=[0, 0.5, 1.0, 1.5, 2.5, 4, 6, 8.0, np.inf])

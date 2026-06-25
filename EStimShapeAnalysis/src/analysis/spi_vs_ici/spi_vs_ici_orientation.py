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
    merged_df, data_description = load_data_for_selection_mode(selection_mode)
    if merged_df.empty:
        print(f"No matching data found for {data_description}")
        return None

    orient_df = load_preferred_orientations()
    if orient_df.empty:
        print("No orientation data available - cannot build orientation-strong plot")
        return None

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
        return None

    frequencies = sorted(strong['frequency'].unique())
    n_cells = strong[['session_id', 'unit_name']].drop_duplicates().shape[0]
    print(f"Orientation-strong SPI vs ICI ({data_description}): "
          f"{len(strong)} (cell, freq) points across {n_cells} cells, "
          f"threshold >= {threshold:.0%} of peak tuning")

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
        ax.scatter(x[sig_mask], y[sig_mask], alpha=0.7, s=60, color='blue', label='sig.')
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


# ---------------------------------------------------------------------------
# Deliverable 2: cycles-per-RF vs orientation tuning depth
# ---------------------------------------------------------------------------

def plot_rf_size_vs_orientation_tuning(selection_mode='mapped_channel',
                                       regression_method='ols', save_path=None):
    """Scatter of cycles per RF (x) vs orientation tuning depth max-min (y).

    cycles per RF = stimulus frequency x RF diameter = ``frequency * 2 * rf_radius``.
    One point per (cell, frequency) that has both orientation tuning and an RF radius.

    Args:
        selection_mode: Channel selection mode (same options as spi_vs_ici.py).
            'mapped_channel' is recommended since it requires RF info.
        regression_method: 'ols' or 'theil-sen'.
        save_path: Optional path to save the figure.
    """
    base_df, data_description = load_data_for_selection_mode(selection_mode)
    if base_df.empty:
        print(f"No matching channels found for {data_description}")
        return None

    orient_df = load_preferred_orientations()
    if orient_df.empty:
        print("No orientation data available - cannot build RF-size vs tuning plot")
        return None

    # Restrict orientation data to the selected channels
    selected = base_df[['session_id', 'unit_name']].drop_duplicates()
    orient_sel = orient_df.merge(selected, on=['session_id', 'unit_name'], how='inner')
    if orient_sel.empty:
        print(f"No orientation data for selected channels ({data_description})")
        return None

    # Attach RF radius (with cluster fallback) and compute cycles per RF
    orient_sel = merge_receptive_field_radius(orient_sel)
    valid = orient_sel['rf_radius'].notna() & (orient_sel['rf_radius'] > 0)
    n_missing = int((~valid).sum())
    if n_missing > 0:
        print(f"WARNING: {n_missing} of {len(orient_sel)} (cell, frequency) points "
              f"lack a valid RF radius and are skipped.")
    orient_sel = orient_sel[valid].copy()

    if orient_sel.empty:
        print("No points with valid RF radius available for RF-size vs tuning plot")
        return None

    # cycles per RF = frequency (cycles/deg) * RF diameter (deg)
    orient_sel['cycles_per_rf'] = orient_sel['frequency'] * 2.0 * orient_sel['rf_radius']

    x = orient_sel['cycles_per_rf'].values
    y = orient_sel['max_minus_min'].values

    slope, intercept, r_value, p_value, r_squared, x_reg = calculate_regression_with_spi_cap(
        x, y, regression_method, None)

    n_cells = orient_sel[['session_id', 'unit_name']].drop_duplicates().shape[0]
    print(f"RF-size vs orientation tuning ({data_description}): "
          f"{len(orient_sel)} (cell, freq) points across {n_cells} cells")

    plt.figure(figsize=(10, 7))
    plt.scatter(x, y, alpha=0.6, s=60, color='purple')

    if len(x_reg) > 1 and not np.isnan(slope):
        line_x = np.linspace(np.min(x_reg), np.max(x_reg), 100)
        plt.plot(line_x, slope * line_x + intercept, 'k-', linewidth=2,
                 label=f'{regression_method.upper()} fit (R²={r_squared:.3f})')
        plt.legend(loc='best')

    plt.xlabel('Cycles per RF (frequency × RF diameter)')
    plt.ylabel('Orientation Tuning (max − min response, spikes/s)')
    plt.title(f'RF Size vs Orientation Tuning\n{data_description}')
    plt.grid(True, alpha=0.3)

    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {len(x)}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved RF-size vs orientation tuning plot: {save_path}")
    plt.show()

    return orient_sel


if __name__ == "__main__":
    # Channel selection mode (see spi_vs_ici.py for options). 'mapped_channel'
    # requires RF info, which is needed for the cycles-per-RF plot.
    selection_mode = 'mapped_channel'
    save_dir = None  # e.g. "/home/connorlab/Documents/plots"

    def _path(name):
        return os.path.join(save_dir, name) if save_dir else None

    # 1) SPI vs ICI for orientation-strong cells/frequencies (tuning >= 70% of peak)
    plot_orientation_strong_spi_vs_ici(
        selection_mode=selection_mode, threshold=0.7,
        regression_method='ols', spi_regression_max=0.3,
        save_path=_path("orientation_strong_spi_vs_ici.png"))

    # 2) Cycles per RF vs orientation tuning (max - min)
    plot_rf_size_vs_orientation_tuning(
        selection_mode=selection_mode, regression_method='ols',
        save_path=_path("rf_size_vs_orientation_tuning.png"))

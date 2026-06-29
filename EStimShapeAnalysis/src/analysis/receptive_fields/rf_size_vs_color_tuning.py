"""Standalone "RF size vs colour tuning" plot.

Scatter of cycles-per-RF (stimulus frequency x RF diameter) against colour tuning
depth (``max_minus_min`` from ``PreferredColors``), one point per (unit, frequency).
The "colors" are the gabor types (Red, Green, Cyan, Orange, RedGreen, CyanOrange),
with isochromatic and isoluminant gabors pooled together; the colour tuning depth is
the max-minus-min response across those types. Colour tuning is z-scored per unit
across its frequencies (so units with different firing rates are comparable), and a
binned mean +/- SEM trend line reveals any preferred number of cycles per RF for
colour tuning.

Mirrors ``rf_size_vs_orientation_tuning.py`` and reuses the RF-radius lookup (with
cluster fallback) from ``spi_vs_ici_preferred_freq.py``.

This sandbox has no pandas/matplotlib/scipy/DB, so the script is validated with
``python -m py_compile`` only; run it for real on a machine with DB access.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from clat.util.connection import Connection
from src.analysis.spi_vs_ici.spi_vs_ici_preferred_freq import merge_receptive_field_radius


def load_color_tuning(filter_type='all'):
    """Load per-(unit, frequency) colour tuning depth from ``PreferredColors``.

    Args:
        filter_type: Channel selection (same options as rf_size_vs_preferred_freq.py).
            - 'all': every PreferredColors row.
            - 'cluster': only cluster channels (JOIN Experiments + ClusterInfo).
            - 'mapped_channel': cluster channels that also have a ReceptiveFieldInfo entry.

    Returns:
        DataFrame ['session_id', 'unit_name', 'frequency', 'max_minus_min'],
        de-duplicated on (session_id, unit_name, frequency), or None if no rows.
    """
    conn = Connection("allen_data_repository")

    if filter_type == 'all':
        query = """
                SELECT session_id, unit_name, frequency, max_minus_min
                FROM PreferredColors
                """
    elif filter_type in ('cluster', 'mapped_channel'):
        rf_join = ""
        if filter_type == 'mapped_channel':
            rf_join = ("\n                         JOIN ReceptiveFieldInfo r "
                       "ON r.session_id = p.session_id AND r.channel = p.unit_name")
        query = f"""
                SELECT p.session_id, p.unit_name, p.frequency, p.max_minus_min
                FROM PreferredColors p
                         JOIN Experiments e ON p.session_id = e.session_id
                         JOIN ClusterInfo c ON e.experiment_id = c.experiment_id
                                            AND p.unit_name = c.channel{rf_join}
                WHERE c.experiment_id LIKE '%isogabor' AND c.gen_id=1
                """
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}. "
                         f"Use 'all', 'cluster', or 'mapped_channel'")

    try:
        conn.execute(query)
        rows = conn.fetch_all()
    except Exception as e:
        print(f"Could not load PreferredColors (table may not exist): {e}")
        return None

    if not rows:
        print(f"No PreferredColors rows found for filter_type='{filter_type}'")
        return None

    df = pd.DataFrame(rows, columns=['session_id', 'unit_name', 'frequency', 'max_minus_min'])
    df['frequency'] = pd.to_numeric(df['frequency'], errors='coerce')
    df['max_minus_min'] = pd.to_numeric(df['max_minus_min'], errors='coerce')
    df = df.dropna(subset=['frequency', 'max_minus_min'])
    return df.drop_duplicates(['session_id', 'unit_name', 'frequency'])


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


def _tuning_label(normalize):
    return {
        'zscore': 'Colour tuning (max − min, z-scored per unit)',
        'max': 'Colour tuning (max − min, normalized to unit max)',
        'none': 'Colour tuning (max − min response, spikes/s)',
    }.get(normalize, 'Colour tuning (max − min)')


def expand_color_tuning(filter_type='all', normalize='zscore'):
    """Build a per-(unit, frequency) cycles-per-RF / colour-tuning dataset.

    For each selected unit, colour tuning depth (``max_minus_min``) is normalized
    across that unit's tested frequencies (per-unit z-score by default), and
    ``cycles_per_rf = frequency * 2 * rf_radius`` is computed.

    Returns a long-form DataFrame, or None if no data.
    Columns: session_id, unit_name, rf_radius, frequency, tuning, norm_tuning, cycles_per_rf.
    """
    df = load_color_tuning(filter_type)
    if df is None or df.empty:
        return None

    df = merge_receptive_field_radius(df)

    # Per-unit normalization is over the unit's full tuning profile (all frequencies),
    # then we keep points with a valid RF radius to plot.
    records = []
    n_skipped_norm = 0
    for (session_id, unit_name), grp in df.groupby(['session_id', 'unit_name']):
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
        print("No colour tuning points available after normalization")
        return None

    valid = long_df['rf_radius'].notna() & (long_df['rf_radius'] > 0)
    n_missing = int((~valid).sum())
    if n_missing > 0:
        print(f"WARNING: {n_missing} of {len(long_df)} (unit, frequency) points "
              f"lack a valid RF radius and are skipped.")
    long_df = long_df[valid].copy()
    if long_df.empty:
        print("No points with valid RF radius available for RF-size vs tuning plot")
        return None

    return long_df


def plot_rf_size_vs_color_tuning(filter_type='all', normalize='zscore',
                                 n_bins=8, bin_edges=None, xlim=None, save_path=None):
    """Cycles per RF (x) vs colour tuning (y), with a binned mean +/- SEM trend.

    One point per (unit, frequency), colour tuning depth (max - min across gabor types)
    z-scored per unit across its frequencies, points colored by stimulus frequency, with
    a black binned mean +/- SEM trend line.

    cycles per RF = stimulus frequency x RF diameter = ``frequency * 2 * rf_radius``.

    Args:
        filter_type: Channel selection ('all', 'cluster', or 'mapped_channel').
        normalize: Per-unit tuning normalization ('zscore', 'max', or 'none').
        n_bins: Number of equal-width cycles-per-RF bins (used only when bin_edges is None).
        bin_edges: Optional explicit bin edges, e.g. [0, 2, 4, 8, np.inf].
        xlim: Optional (xmin, xmax) display crop (all points still used for the trend).
        save_path: Optional path to save the figure.
    """
    long_df = expand_color_tuning(filter_type, normalize)
    if long_df is None or long_df.empty:
        return None

    y_col = 'tuning' if normalize == 'none' else 'norm_tuning'
    x = long_df['cycles_per_rf'].values
    y = long_df[y_col].values

    n_cells = long_df[['session_id', 'unit_name']].drop_duplicates().shape[0]
    print(f"RF-size vs colour tuning (filter_type='{filter_type}', normalize='{normalize}'): "
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
    ax.set_title(f'Colour tuning vs cycles per RF (filter_type={filter_type})\n'
                 f'(n={len(long_df)} unit×frequency points, {n_cells} units)', fontsize=13)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9, title='Stimulus frequency')
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved RF-size vs colour tuning plot: {save_path}")
    plt.show()

    return long_df


if __name__ == "__main__":
    # 'all', 'cluster', or 'mapped_channel' ('mapped_channel' requires RF info).
    filter_type = 'mapped_channel'
    save_dir = None  # e.g. "/home/connorlab/Documents/plots"
    cycles_xlim = [0,10]  # e.g. (0, 8) to crop the display (all points still feed the trend)

    def _path(name):
        return os.path.join(save_dir, name) if save_dir else None

    plot_rf_size_vs_color_tuning(
        filter_type=filter_type, normalize='zscore', n_bins=8,
        xlim=cycles_xlim,
        bin_edges=[0, 0.5, 1.0, 1.5, 2.5, 4, 6, 8.0, np.inf],
        save_path=_path("rf_size_vs_color_tuning.png"))

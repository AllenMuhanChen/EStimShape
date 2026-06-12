"""Standalone "RF size vs preferred frequency" plot.

Plots the relationship between a unit's receptive-field size and its preferred
(spatial) frequency, reusing the RF-radius lookup (with cluster fallback) from
``spi_vs_ici_preferred_freq.py``.

Three views are produced (all theory-motivated by the expectation that preferred
spatial frequency is inversely related to RF size):

  1. Scatter of RF size vs preferred frequency, with a linear regression. Because
     the stored ``preferred_frequency`` is discrete (typically {0.5, 1, 2, 4}),
     this view can optionally be drawn on log-log axes (the natural test of a
     ``freq ~ 1/size`` power law, slope ~ -1).
  2. Box plot of RF size grouped by the discrete preferred frequency, which avoids
     the vertical-stripe artifact of the raw scatter.
  3. Scatter of RF size vs a *continuous* preferred frequency derived from the
     per-frequency response profile (response-weighted center-of-mass), again with
     a regression and optional log-log axes.

A summary derived quantity, "cycles across the RF at the preferred frequency"
(``preferred_frequency * 2 * rf_radius``), is also reported.

This sandbox has no pandas/matplotlib/scipy/DB, so the script is validated with
``python -m py_compile`` only; run it for real on a machine with DB access.
"""

import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from clat.util.connection import Connection
from src.analysis.spi_vs_ici.spi_vs_ici_preferred_freq import merge_receptive_field_radius


# Frequencies actually used by the stimulus set (for axis ticks / grouping).
ALLOWED_FREQUENCIES = [0.5, 1.0, 2.0, 4.0]


def load_preferred_frequency_data(filter_type='all'):
    """Load preferred-frequency rows, optionally restricted to cluster channels.

    Args:
        filter_type: Channel selection.
            - 'all': every PreferredFrequencies row.
            - 'cluster': only channels that are cluster channels (JOIN Experiments +
              ClusterInfo, matching spi_vs_ici_preferred_freq.py / spi_ici_clusters.py).
            - 'mapped_channel': cluster channels that also have a ReceptiveFieldInfo
              entry for the same (session_id, channel).

    Returns:
        DataFrame with columns ['session_id', 'unit_name', 'preferred_frequency',
        'all_freq_responses'], de-duplicated on (session_id, unit_name), or None if
        no rows are found.
    """
    conn = Connection("allen_data_repository")

    if filter_type == 'all':
        query = """
                SELECT session_id, unit_name, preferred_frequency, all_freq_responses
                FROM PreferredFrequencies
                """
    elif filter_type in ('cluster', 'mapped_channel'):
        # Cluster channels: PreferredFrequencies.unit_name == ClusterInfo.channel,
        # with Experiments mapping experiment_id <-> session_id (see
        # load_cluster_based_data in spi_vs_ici_preferred_freq.py).
        rf_join = ""
        if filter_type == 'mapped_channel':
            rf_join = ("\n                         JOIN ReceptiveFieldInfo r "
                       "ON r.session_id = p.session_id AND r.channel = p.unit_name")
        query = f"""
                SELECT p.session_id, p.unit_name, p.preferred_frequency, p.all_freq_responses
                FROM PreferredFrequencies p
                         JOIN Experiments e ON p.session_id = e.session_id
                         JOIN ClusterInfo c ON e.experiment_id = c.experiment_id
                                            AND p.unit_name = c.channel{rf_join}
                """
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}. "
                         f"Use 'all', 'cluster', or 'mapped_channel'")

    conn.execute(query)
    rows = conn.fetch_all()

    if not rows:
        print(f"No PreferredFrequencies rows found for filter_type='{filter_type}'")
        return None

    df = pd.DataFrame(rows, columns=['session_id', 'unit_name',
                                     'preferred_frequency', 'all_freq_responses'])

    # DB FLOATs sometimes come back as Decimal/str.
    df['preferred_frequency'] = pd.to_numeric(df['preferred_frequency'], errors='coerce')
    df = df.dropna(subset=['preferred_frequency'])
    df = df.drop_duplicates(['session_id', 'unit_name'])

    print(f"Loaded {len(df)} preferred-frequency rows (filter_type='{filter_type}')")
    return df


def compute_continuous_preferred_frequency(all_freq_responses):
    """Response-weighted center-of-mass frequency from the per-frequency profile.

    ``all_freq_responses`` is a JSON string mapping ``{frequency: max_response}``.
    Returns ``sum(f * r) / sum(r)`` over frequencies with positive response, which
    is a continuous analog of the (discrete) preferred frequency. Negative responses
    are clipped to zero so they cannot pull the center of mass to nonsensical values.

    Returns:
        float center-of-mass frequency, or NaN if it can't be computed.
    """
    try:
        responses = json.loads(all_freq_responses)
    except (TypeError, ValueError):
        return np.nan

    freqs = []
    weights = []
    for freq, response in responses.items():
        try:
            f = float(freq)
            r = float(response)
        except (TypeError, ValueError):
            continue
        freqs.append(f)
        weights.append(max(r, 0.0))  # clip negatives so they don't skew the COM

    if not freqs:
        return np.nan
    freqs = np.asarray(freqs)
    weights = np.asarray(weights)
    total = weights.sum()
    if total <= 0:
        return np.nan
    return float(np.sum(freqs * weights) / total)


def load_rf_size_vs_preferred_freq_data(filter_type='all'):
    """Load and assemble the analysis DataFrame.

    Queries PreferredFrequencies, attaches RF radius (with cluster fallback) via
    ``merge_receptive_field_radius``, drops rows without a usable radius, and adds
    derived columns.

    Returns:
        DataFrame with at least ['session_id', 'unit_name', 'preferred_frequency',
        'rf_radius', 'rf_diameter', 'sqrt_area', 'continuous_preferred_frequency',
        'cycles_across_rf'], or None if no usable data.
    """
    df = load_preferred_frequency_data(filter_type)
    if df is None or df.empty:
        return None

    # Reuse the shared RF-radius lookup (direct match + cluster fallback).
    df = merge_receptive_field_radius(df)

    n_total = len(df)
    df = df[df['rf_radius'].notna() & (df['rf_radius'] > 0)].copy()
    n_dropped = n_total - len(df)
    if n_dropped > 0:
        print(f"Dropped {n_dropped} of {n_total} rows lacking a usable RF radius")
    if df.empty:
        print("No rows with a usable RF radius; nothing to plot")
        return None

    # Continuous preferred frequency from the response profile.
    df['continuous_preferred_frequency'] = df['all_freq_responses'].apply(
        compute_continuous_preferred_frequency)

    # Derived RF-size measures and the dimensionless cycles-across-RF quantity.
    df['rf_diameter'] = 2.0 * df['rf_radius']
    df['sqrt_area'] = np.sqrt(np.pi * df['rf_radius'] ** 2)
    df['cycles_across_rf'] = df['preferred_frequency'] * 2.0 * df['rf_radius']

    print(f"Analysis dataset: {len(df)} units with RF size and preferred frequency")
    return df


def _fit_regression(x, y, log_log=False):
    """Linear regression of y on x (optionally in log10-log10 space).

    Returns:
        dict with slope, intercept, r_value, r_squared, p_value, n, and log_log;
        or None if fewer than two finite points are available.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if log_log:
        mask &= (x > 0) & (y > 0)
    x = x[mask]
    y = y[mask]
    if len(x) < 2:
        return None

    fx = np.log10(x) if log_log else x
    fy = np.log10(y) if log_log else y
    slope, intercept, r_value, p_value, _ = stats.linregress(fx, fy)
    return {
        'slope': slope,
        'intercept': intercept,
        'r_value': r_value,
        'r_squared': r_value ** 2,
        'p_value': p_value,
        'n': len(x),
        'log_log': log_log,
    }


def _draw_regression_line(ax, fit, x_values, color='black'):
    """Draw the fitted regression line spanning the data x-range."""
    if fit is None:
        return
    x_values = np.asarray(x_values, dtype=float)
    x_values = x_values[np.isfinite(x_values)]
    if fit['log_log']:
        x_values = x_values[x_values > 0]
    if len(x_values) < 2:
        return

    x_line = np.linspace(x_values.min(), x_values.max(), 200)
    if fit['log_log']:
        y_line = 10 ** (fit['slope'] * np.log10(x_line) + fit['intercept'])
    else:
        y_line = fit['slope'] * x_line + fit['intercept']
    ax.plot(x_line, y_line, color=color, linewidth=2.5,
            label=f"fit: slope={fit['slope']:.2f}, R²={fit['r_squared']:.2f}, "
                  f"p={fit['p_value']:.3g}, n={fit['n']}")


def _stats_text(fit):
    """Format a regression-stats text box string."""
    if fit is None:
        return "no regression (n<2)"
    space = "log-log" if fit['log_log'] else "linear"
    return (f"{space} fit\nslope = {fit['slope']:.3f}\nr = {fit['r_value']:.3f}\n"
            f"R² = {fit['r_squared']:.3f}\np = {fit['p_value']:.3g}\nn = {fit['n']}")


def plot_rf_size_vs_preferred_frequency(df, save_path=None, log_log=False,
                                        size_col='rf_radius', freq_col='preferred_frequency'):
    """View 1/3: scatter of RF size vs (discrete or continuous) preferred frequency.

    Args:
        df: Analysis DataFrame from load_rf_size_vs_preferred_freq_data.
        save_path: Where to save the figure (None -> display only).
        log_log: If True, use log-log axes and fit a power law (slope ~ -1 expected).
        size_col: RF-size column for the x-axis ('rf_radius', 'rf_diameter', or 'sqrt_area').
        freq_col: Frequency column for the y-axis ('preferred_frequency' or
            'continuous_preferred_frequency').
    """
    data = df[[size_col, freq_col]].apply(pd.to_numeric, errors='coerce').dropna()
    x = data[size_col].values
    y = data[freq_col].values

    fit = _fit_regression(x, y, log_log=log_log)

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(x, y, s=60, alpha=0.6, color='tab:blue', edgecolors='black', linewidths=0.4)
    _draw_regression_line(ax, fit, x, color='tab:red')

    if log_log:
        ax.set_xscale('log')
        ax.set_yscale('log')

    ax.set_xlabel(_axis_label(size_col), fontsize=13)
    ax.set_ylabel(_axis_label(freq_col), fontsize=13)
    ax.set_title(f'RF size vs preferred frequency'
                 f'{" (log-log)" if log_log else ""}\n(n={len(data)} units)', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.text(0.02, 0.02, _stats_text(fit), transform=ax.transAxes,
            va='bottom', ha='left', fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.85))
    if fit is not None:
        ax.legend(loc='upper right', fontsize=9)
    fig.tight_layout()

    _save(fig, save_path)
    _print_fit(f"Scatter ({size_col} vs {freq_col}{', log-log' if log_log else ''})", fit)
    return fit


def plot_rf_size_by_frequency_box(df, save_path=None, size_col='rf_radius'):
    """View 2/3: box plot of RF size grouped by the discrete preferred frequency.

    Avoids the vertical-stripe artifact of scattering a discrete frequency.
    """
    present_freqs = [f for f in ALLOWED_FREQUENCIES
                     if (df['preferred_frequency'] == f).any()]
    # Include any non-standard preferred frequencies that appear in the data.
    extra = sorted(set(df['preferred_frequency'].dropna().unique()) - set(present_freqs))
    freqs = present_freqs + list(extra)

    grouped = [pd.to_numeric(df.loc[df['preferred_frequency'] == f, size_col],
                             errors='coerce').dropna().values
               for f in freqs]

    fig, ax = plt.subplots(figsize=(9, 7))
    positions = np.arange(1, len(freqs) + 1)
    ax.boxplot(grouped, positions=positions, widths=0.6, showmeans=True)

    # Overlay jittered points for transparency about sample size.
    rng = np.random.default_rng(0)
    for pos, vals in zip(positions, grouped):
        if len(vals):
            jitter = rng.uniform(-0.15, 0.15, size=len(vals))
            ax.scatter(pos + jitter, vals, s=20, alpha=0.4, color='tab:blue')

    ax.set_xticks(positions)
    ax.set_xticklabels([f'{f:g}' for f in freqs])
    ax.set_xlabel('Preferred frequency', fontsize=13)
    ax.set_ylabel(_axis_label(size_col), fontsize=13)
    counts = ", ".join(f"{f:g}:{len(v)}" for f, v in zip(freqs, grouped))
    ax.set_title(f'RF size grouped by preferred frequency\n(n per group — {counts})',
                 fontsize=13)
    ax.grid(True, axis='y', alpha=0.3)
    fig.tight_layout()

    _save(fig, save_path)
    print("\nBox plot — RF size by preferred frequency:")
    for f, v in zip(freqs, grouped):
        if len(v):
            print(f"  {f:g} Hz: n={len(v)}, median {size_col}={np.median(v):.3f}, "
                  f"mean={np.mean(v):.3f}")


def _axis_label(col):
    return {
        'rf_radius': 'RF radius (deg)',
        'rf_diameter': 'RF diameter (deg)',
        'sqrt_area': 'sqrt(RF area)  sqrt(π r²) (deg)',
        'preferred_frequency': 'Preferred frequency (discrete)',
        'continuous_preferred_frequency': 'Continuous preferred frequency (resp.-weighted)',
        'cycles_across_rf': 'Cycles across RF (freq × diameter)',
    }.get(col, col)


def _save(fig, save_path):
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")


def _print_fit(label, fit):
    print(f"\n{label}:")
    if fit is None:
        print("  (too few points for a regression)")
        return
    print(f"  n={fit['n']}, slope={fit['slope']:.3f}, r={fit['r_value']:.3f}, "
          f"R²={fit['r_squared']:.3f}, p={fit['p_value']:.3g}"
          f"{'  [log-log]' if fit['log_log'] else ''}")


def create_rf_size_vs_preferred_freq_plots(save_dir=None, filter_type='all',
                                           size_col='rf_radius', log_log=True):
    """Build all RF-size vs preferred-frequency plots and print summary stats.

    Args:
        save_dir: Directory to save figures (created if needed). If None, figures are
            only displayed.
        filter_type: 'all', 'cluster', or 'mapped_channel' (see load_preferred_frequency_data).
        size_col: RF-size measure for the x-axis ('rf_radius', 'rf_diameter', 'sqrt_area').
        log_log: If True, also draw the scatter views on log-log axes (power-law test).
    """
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)

    df = load_rf_size_vs_preferred_freq_data(filter_type)
    if df is None or df.empty:
        print("No data available for plotting")
        return

    suffix = f"_{filter_type}"

    # View 1: discrete preferred frequency.
    plot_rf_size_vs_preferred_frequency(
        df, _path(save_dir, f"01_rf_size_vs_preferred_freq{suffix}.png"),
        log_log=False, size_col=size_col, freq_col='preferred_frequency')
    if log_log:
        plot_rf_size_vs_preferred_frequency(
            df, _path(save_dir, f"01b_rf_size_vs_preferred_freq_loglog{suffix}.png"),
            log_log=True, size_col=size_col, freq_col='preferred_frequency')

    # View 2: box plot by discrete preferred frequency.
    plot_rf_size_by_frequency_box(
        df, _path(save_dir, f"02_rf_size_by_preferred_freq_box{suffix}.png"),
        size_col=size_col)

    # View 3: continuous preferred frequency.
    plot_rf_size_vs_preferred_frequency(
        df, _path(save_dir, f"03_rf_size_vs_continuous_freq{suffix}.png"),
        log_log=False, size_col=size_col, freq_col='continuous_preferred_frequency')
    if log_log:
        plot_rf_size_vs_preferred_frequency(
            df, _path(save_dir, f"03b_rf_size_vs_continuous_freq_loglog{suffix}.png"),
            log_log=True, size_col=size_col, freq_col='continuous_preferred_frequency')

    # Summary of the dimensionless cycles-across-RF quantity.
    cycles = pd.to_numeric(df['cycles_across_rf'], errors='coerce').dropna()
    if not cycles.empty:
        print(f"\nCycles across RF at preferred frequency (freq × 2 × radius):")
        print(f"  n={len(cycles)}, mean={cycles.mean():.3f}, median={cycles.median():.3f}, "
              f"min={cycles.min():.3f}, max={cycles.max():.3f}")

    plt.show()


def _path(save_dir, name):
    return os.path.join(save_dir, name) if save_dir else None


if __name__ == "__main__":
    # filter_type: 'all' (every PreferredFrequencies row), 'cluster' (cluster channels
    # only), or 'mapped_channel' (cluster channels that also have a mapped RF).
    # size_col: 'rf_radius' (default), 'rf_diameter', or 'sqrt_area'.
    # log_log=True additionally produces log-log power-law versions of the scatter views.
    create_rf_size_vs_preferred_freq_plots(
        save_dir="/home/connorlab/Documents/plots/rf_size_vs_preferred_freq",
        filter_type='all',
        size_col='rf_radius',
        log_log=True,
    )

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


def _normalize_responses(values, method):
    """Normalize a single unit's responses across its tested frequencies.

    Args:
        values: 1-D array of that unit's responses (one per tested frequency).
        method: 'zscore' (per-unit z-score), 'max' (divide by the unit's max), or
            'none' (raw values).

    Returns:
        Array of normalized responses, or None if normalization is undefined for
        this unit (e.g. zero variance for z-score, non-positive max for 'max').
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
    raise ValueError(f"Unknown normalize method: {method}. Use 'zscore', 'max', or 'none'")


def expand_frequency_responses(df, normalize='zscore'):
    """Explode all_freq_responses into one row per (unit, tested frequency).

    For each unit and each frequency in its response profile, computes
    ``cycles_per_rf = frequency * 2 * rf_radius`` and the (optionally per-unit
    normalized) response, giving a population spatial-frequency tuning dataset in
    RF-normalized units.

    Args:
        df: Analysis DataFrame (must include 'all_freq_responses' and 'rf_radius').
        normalize: Per-unit response normalization ('zscore', 'max', or 'none').

    Returns:
        Long-form DataFrame with ['session_id', 'unit_name', 'rf_radius', 'frequency',
        'response', 'norm_response', 'cycles_per_rf'].
    """
    records = []
    n_skipped = 0
    for row in df.itertuples(index=False):
        try:
            responses = json.loads(row.all_freq_responses)
        except (TypeError, ValueError):
            n_skipped += 1
            continue

        freqs, vals = [], []
        for freq, resp in responses.items():
            try:
                freqs.append(float(freq))
                vals.append(float(resp))
            except (TypeError, ValueError):
                continue
        if not freqs:
            n_skipped += 1
            continue

        norm = _normalize_responses(vals, normalize)
        if norm is None:
            n_skipped += 1
            continue

        for freq, raw, nv in zip(freqs, vals, norm):
            records.append({
                'session_id': row.session_id,
                'unit_name': row.unit_name,
                'rf_radius': row.rf_radius,
                'frequency': freq,
                'response': raw,
                'norm_response': nv,
                'cycles_per_rf': freq * 2.0 * row.rf_radius,
            })

    if n_skipped > 0:
        print(f"Expanded responses: skipped {n_skipped} unit(s) "
              f"(unparseable profile or undefined '{normalize}' normalization)")
    return pd.DataFrame.from_records(records)


def _response_label(normalize):
    return {
        'zscore': 'Response (z-scored per unit)',
        'max': 'Response (normalized to unit max)',
        'none': 'Response (raw)',
    }.get(normalize, 'Response')


def load_solid_preference_indices():
    """Load per-unit Solid Preference Index and its significance p-value.

    Returns:
        DataFrame ['session_id', 'unit_name', 'solid_preference_index', 'spi_p_value'],
        de-duplicated on (session_id, unit_name), or None if no rows.
    """
    conn = Connection("allen_data_repository")
    conn.execute("""
                 SELECT session_id, unit_name, solid_preference_index, p_value
                 FROM SolidPreferenceIndices
                 """)
    rows = conn.fetch_all()
    if not rows:
        print("No SolidPreferenceIndices rows found")
        return None
    df = pd.DataFrame(rows, columns=['session_id', 'unit_name',
                                     'solid_preference_index', 'spi_p_value'])
    df['solid_preference_index'] = pd.to_numeric(df['solid_preference_index'], errors='coerce')
    df['spi_p_value'] = pd.to_numeric(df['spi_p_value'], errors='coerce')
    return df.drop_duplicates(['session_id', 'unit_name'])


def load_isochromatic_preference_indices():
    """Load per-(unit, frequency) Isochromatic Preference Index.

    Unlike the solid index, this is stored per stimulus frequency and has no
    significance p-value.

    Returns:
        DataFrame ['session_id', 'unit_name', 'frequency', 'isochromatic_preference_index'],
        de-duplicated on (session_id, unit_name, frequency), or None if no rows.
    """
    conn = Connection("allen_data_repository")
    conn.execute("""
                 SELECT session_id, unit_name, frequency, isochromatic_preference_index
                 FROM IsochromaticPreferenceIndices
                 """)
    rows = conn.fetch_all()
    if not rows:
        print("No IsochromaticPreferenceIndices rows found")
        return None
    df = pd.DataFrame(rows, columns=['session_id', 'unit_name', 'frequency',
                                     'isochromatic_preference_index'])
    df['frequency'] = pd.to_numeric(df['frequency'], errors='coerce')
    df['isochromatic_preference_index'] = pd.to_numeric(
        df['isochromatic_preference_index'], errors='coerce')
    return df.drop_duplicates(['session_id', 'unit_name', 'frequency'])


def plot_cycles_per_rf_vs_response(df, save_path=None, normalize='zscore', n_bins=8,
                                   bin_edges=None, xlim=None, color_by='frequency'):
    """View 4: response vs cycles-per-RF (freq × RF diameter) across all frequencies.

    One point per (unit, tested frequency), with a binned mean ± SEM trend line that
    reveals any preferred number of cycles per RF.

    Points can be colored three ways via ``color_by``:
      - 'frequency': discrete color per stimulus frequency (default).
      - 'spi': continuous color by the unit's Solid Preference Index, with
        non-significant points (solid-pref p >= 0.05) drawn at lower alpha.
      - 'ici': continuous color by the per-(unit, frequency) Isochromatic Preference
        Index. This index has no significance statistic, so all points share one alpha.

    Args:
        df: Analysis DataFrame from load_rf_size_vs_preferred_freq_data.
        save_path: Where to save the figure (None -> display only).
        normalize: Per-unit response normalization ('zscore', 'max', or 'none').
        n_bins: Number of equal-width cycles-per-RF bins for the trend line
            (used only when bin_edges is None).
        bin_edges: Optional explicit bin edges for the trend line, e.g.
            [0, 1, 2, 4, 8] gives bins [0,1], [1,2], [2,4], [4,8]. Overrides n_bins.
            Use np.inf for an open final bin, e.g. [0, 2, 4, 8, np.inf].
        xlim: Optional (xmin, xmax) cycles-per-RF range for the x-axis. This is a
            display crop only — all points are still used for the binned trend.
        color_by: Point coloring ('frequency', 'spi', or 'ici').
    """
    long_df = expand_frequency_responses(df, normalize=normalize)
    if long_df.empty:
        print("No (unit, frequency) points available for cycles-per-RF plot")
        return None

    # Attach the coloring variable when needed (SPI per unit, ICI per unit×frequency).
    color_col = None
    if color_by == 'spi':
        spi_df = load_solid_preference_indices()
        if spi_df is None:
            return None
        long_df = long_df.merge(spi_df, on=['session_id', 'unit_name'], how='left')
        color_col = 'solid_preference_index'
    elif color_by == 'ici':
        iso_df = load_isochromatic_preference_indices()
        if iso_df is None:
            return None
        long_df = long_df.merge(iso_df, on=['session_id', 'unit_name', 'frequency'], how='left')
        color_col = 'isochromatic_preference_index'
    elif color_by != 'frequency':
        raise ValueError(f"Unknown color_by: {color_by}. Use 'frequency', 'spi', or 'ici'")

    # Drop points lacking the coloring value so the color scale is meaningful.
    if color_col is not None:
        n_before = len(long_df)
        long_df = long_df[long_df[color_col].notna()].copy()
        n_missing = n_before - len(long_df)
        if n_missing > 0:
            print(f"color_by='{color_by}': skipped {n_missing} point(s) without a {color_col}")
        if long_df.empty:
            print(f"No points with a {color_col}; nothing to plot for color_by='{color_by}'")
            return None

    y_col = 'response' if normalize == 'none' else 'norm_response'
    x = long_df['cycles_per_rf'].values
    y = long_df[y_col].values

    fig, ax = plt.subplots(figsize=(9, 7))

    if color_col is None:
        # Discrete color per stimulus frequency.
        freqs = sorted(long_df['frequency'].unique())
        cmap = plt.cm.viridis
        for i, freq in enumerate(freqs):
            m = long_df['frequency'] == freq
            ax.scatter(long_df.loc[m, 'cycles_per_rf'], long_df.loc[m, y_col],
                       s=45, alpha=0.5, color=cmap(i / max(1, len(freqs) - 1)),
                       edgecolors='none', label=f'{freq:g} Hz')
    else:
        # Continuous color by a preference index, symmetric about 0 (indices span [-1, 1]).
        cvals = long_df[color_col].values
        vmax = float(np.nanmax(np.abs(cvals))) if len(cvals) else 1.0
        vmax = vmax if np.isfinite(vmax) and vmax > 0 else 1.0
        cnorm = plt.Normalize(vmin=-vmax, vmax=vmax)
        cmap = plt.cm.coolwarm
        rgba = cmap(cnorm(cvals))
        if color_by == 'spi':
            # Lower alpha for non-significant (or missing-p) solid preferences.
            sig = long_df['spi_p_value'].notna() & (long_df['spi_p_value'] < 0.05)
            rgba[:, 3] = np.where(sig.values, 0.85, 0.15)
        else:
            rgba[:, 3] = 0.6
        ax.scatter(x, y, s=45, c=rgba, edgecolors='none')
        sm = plt.cm.ScalarMappable(norm=cnorm, cmap=cmap)
        sm.set_array([])
        fig.colorbar(sm, ax=ax, label=_color_label(color_by))

    # Binned mean ± SEM trend across all points.
    finite = np.isfinite(x) & np.isfinite(y)
    xb, yb = x[finite], y[finite]
    if len(xb) >= 2 and xb.min() < xb.max():
        if bin_edges is not None:
            edges = np.asarray(bin_edges, dtype=float)
        else:
            edges = np.linspace(xb.min(), xb.max(), n_bins + 1)
        n_bin = len(edges) - 1
        # digitize returns 1..n_bin for in-range points; clip the closed final edge.
        idx = np.digitize(xb, edges) - 1
        centers, means, sems = [], [], []
        for b in range(n_bin):
            sel = (idx == b) if b < n_bin - 1 else (idx == b) | (xb == edges[-1])
            if sel.sum() > 0:
                # For an open (inf) edge, anchor the marker just past the last finite edge.
                hi = edges[b + 1] if np.isfinite(edges[b + 1]) else xb[sel].max()
                centers.append(0.5 * (edges[b] + hi))
                means.append(yb[sel].mean())
                sems.append(yb[sel].std(ddof=1) / np.sqrt(sel.sum()) if sel.sum() > 1 else 0.0)
        ax.errorbar(centers, means, yerr=sems, color='black', linewidth=2.5,
                    marker='o', capsize=3, zorder=5, label='binned mean ± SEM')

    if normalize == 'zscore':
        ax.axhline(0, color='gray', linestyle='--', alpha=0.5)

    if xlim is not None:
        ax.set_xlim(xlim)
    ax.set_xlabel('Cycles per RF (frequency × RF diameter)', fontsize=13)
    ax.set_ylabel(_response_label(normalize), fontsize=13)
    title_suffix = {'spi': ' — colored by Solid Preference Index',
                    'ici': ' — colored by Isochromatic Preference Index'}.get(color_by, '')
    ax.set_title(f'Response vs cycles per RF{title_suffix}\n'
                 f'(n={len(long_df)} unit×frequency points, '
                 f'{long_df[["session_id", "unit_name"]].drop_duplicates().shape[0]} units)',
                 fontsize=13)
    ax.grid(True, alpha=0.3)
    if color_col is None:
        ax.legend(loc='best', fontsize=9, title='Stimulus frequency')
    elif ax.get_legend_handles_labels()[0]:
        # SPI/ICI use a colorbar; keep only the trend-line entry.
        ax.legend(loc='best', fontsize=9)
    fig.tight_layout()

    _save(fig, save_path)
    print(f"\nResponse vs cycles per RF (normalize='{normalize}', color_by='{color_by}'):")
    print(f"  {len(long_df)} unit×frequency points; "
          f"cycles_per_rf range [{np.nanmin(x):.3f}, {np.nanmax(x):.3f}]")
    return long_df


def _color_label(color_by):
    return {
        'spi': 'Solid Preference Index',
        'ici': 'Isochromatic Preference Index',
    }.get(color_by, color_by)


def create_rf_size_vs_preferred_freq_plots(save_dir=None, filter_type='all',
                                           size_col='rf_radius', log_log=True,
                                           response_normalize='zscore',
                                           cycles_bin_edges=None, cycles_n_bins=8,
                                           cycles_xlim=None):
    """Build all RF-size vs preferred-frequency plots and print summary stats.

    Args:
        save_dir: Directory to save figures (created if needed). If None, figures are
            only displayed.
        filter_type: 'all', 'cluster', or 'mapped_channel' (see load_preferred_frequency_data).
        size_col: RF-size measure for the x-axis ('rf_radius', 'rf_diameter', 'sqrt_area').
        log_log: If True, also draw the scatter views on log-log axes (power-law test).
        response_normalize: Per-unit response normalization for the cycles-per-RF view
            ('zscore', 'max', or 'none').
        cycles_bin_edges: Optional explicit cycles-per-RF bin edges for the View 4 trend
            line, e.g. [0, 2, 4, 8, np.inf]. Overrides cycles_n_bins.
        cycles_n_bins: Number of equal-width cycles-per-RF bins for View 4 when
            cycles_bin_edges is None.
        cycles_xlim: Optional (xmin, xmax) x-axis range for the View 4 cycles-per-RF
            plot (display crop only; all points still used for the trend).
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

    # View 4: response vs cycles-per-RF across all tested frequencies.
    # 4a: colored by stimulus frequency; 4b: by Solid Preference Index (alpha by
    # significance); 4c: by Isochromatic Preference Index (no significance).
    cycles_kwargs = dict(normalize=response_normalize, n_bins=cycles_n_bins,
                         bin_edges=cycles_bin_edges, xlim=cycles_xlim)
    plot_cycles_per_rf_vs_response(
        df, _path(save_dir, f"04_cycles_per_rf_vs_response{suffix}.png"),
        color_by='frequency', **cycles_kwargs)
    plot_cycles_per_rf_vs_response(
        df, _path(save_dir, f"04b_cycles_per_rf_vs_response_spi{suffix}.png"),
        color_by='spi', **cycles_kwargs)
    plot_cycles_per_rf_vs_response(
        df, _path(save_dir, f"04c_cycles_per_rf_vs_response_ici{suffix}.png"),
        color_by='ici', **cycles_kwargs)

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
        response_normalize='zscore',
        # Customize the cycles-per-RF trend bins here; None -> cycles_n_bins equal-width
        # bins. Example: [0, 2, 4, 8, np.inf] for bins [0,2], [2,4], [4,8], [8,inf].
        cycles_bin_edges=None,
        cycles_n_bins=8,
        # Crop the View 4 x-axis, e.g. (0, 10); None auto-scales to the data.
        cycles_xlim=None,
    )

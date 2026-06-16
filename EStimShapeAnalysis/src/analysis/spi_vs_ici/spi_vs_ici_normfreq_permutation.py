"""Normalized-frequency binning of SPI vs ICI, with permutation tests.

This is a standalone companion to ``spi_vs_ici_preferred_freq.py``. It reuses the
exact same data-filtering mechanics (``load_and_filter_data`` and the cluster /
double / selectivity / mapped-channel loaders) and the same normalized-frequency
binning, but focuses only on the normalized-frequency plots and adds two
permutation tests.

Note on the "normalized frequency" axis
---------------------------------------
The quantity is computed as ``frequency * 2 * rf_radius`` i.e.
``stimulus frequency (cycles/deg) x RF diameter (deg) = cycles across the RF``.
It is a *multiplication* by RF size, so the original "freq / RF radius" labels
were incorrect; this script labels it "freq x RF diameter (= freq x 2*radius)".

Permutation tests
-----------------
Both tests shuffle a *unit-level* attribute across units (SPI and RF radius are
both single values per unit; only ICI varies with stimulus frequency). Shuffling
at the unit level keeps each unit's set of ICI measurements intact and avoids
pseudo-replication from a unit contributing several frequency rows.

1. ``permutation_test_scramble_rf`` shuffles the RF radius across units. This
   randomizes which normalized-frequency bin each point lands in while leaving
   the global SPI-ICI relationship and the global ICI distribution untouched.
   It is therefore the null for "does the trend depend on normalized RF?". For
   that question the meaningful statistic is the *spread of the per-bin
   statistics across bins* (reported as the between-bin heterogeneity test);
   the per-bin "observed > null" comparisons are also reported but should be
   read with the caveat in the module docstring / chat answer.

2. ``permutation_test_scramble_spi`` shuffles (SPI, p_value) across units,
   breaking the SPI-ICI pairing while leaving the normalized-frequency bins
   fixed. This is the null for "does SPI have an effect on ICI?" (per bin and
   per significance category).

Test statistics, per normalized-frequency bin and per significance category
(``All``, ``Sig. 2D``, ``Non-sig.``, ``Sig. 3D``):
    * ``slope`` of the ICI ~ SPI linear fit (signed; positive = SPI predicts ICI
      in the expected 3D/isochromatic direction).
    * ``frac_pos`` = fraction of points with isochromatic preference index > 0.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.spi_vs_ici.spi_vs_ici_preferred_freq import (
    REGRESSION_CATEGORIES,
    add_plot_formatting,
    categorize_points,
    linregress_with_spi_cap,
    load_and_filter_data,
)

# Axis / title label for the normalized-frequency quantity (freq * 2 * rf_radius).
NORMFREQ_LABEL = "Normalized frequency (freq × RF diameter = freq × 2·radius)"

# Significance categories used for every per-bin statistic. "All" pools every
# point in the bin; the remaining three match REGRESSION_CATEGORIES.
CATEGORIES = ["All"] + [label for label, _ in REGRESSION_CATEGORIES]


# ---------------------------------------------------------------------------
# Binning (quiet variant, safe to call thousands of times)
# ---------------------------------------------------------------------------
def add_unit_key(data):
    """Return a copy of data with a per-unit key column (session_id + unit_name)."""
    data = data.copy()
    data["unit_key"] = (data["session_id"].astype(str) + "::" +
                        data["unit_name"].astype(str))
    return data


def compute_normfreq_bins_quiet(data, n_bins=4, bin_edges=None):
    """Add 'normalized_frequency' and 'nf_bin' columns without printing.

    Mirrors ``compute_normalized_frequency_bins`` from the original module but
    silent (so it can run inside the permutation loops). Points lacking a valid
    RF radius (NaN or <= 0) are dropped.

    Returns the binned DataFrame, or None if it cannot be binned.
    """
    data = data.copy()
    if "rf_radius" not in data.columns:
        return None

    valid = data["rf_radius"].notna() & (data["rf_radius"] > 0)
    data = data[valid].copy()
    if data.empty:
        return None

    # Normalized frequency = stimulus frequency x RF diameter (= freq x 2*radius).
    data["normalized_frequency"] = data["frequency"] * 2 * data["rf_radius"]

    if bin_edges is not None:
        try:
            data["nf_bin"] = pd.cut(data["normalized_frequency"], bins=list(bin_edges),
                                    include_lowest=True)
        except ValueError:
            return None
    else:
        if len(data) < n_bins:
            return None
        try:
            data["nf_bin"] = pd.qcut(data["normalized_frequency"], n_bins, duplicates="drop")
        except ValueError:
            return None

    return data


# ---------------------------------------------------------------------------
# Per-bin / per-category statistics
# ---------------------------------------------------------------------------
def _fit_slope(x, y, spi_regression_max=None):
    """Signed slope of ICI ~ SPI; NaN when the fit is undefined.

    Returns NaN when fewer than two points survive the SPI cap or when all
    surviving x (SPI) values are identical (e.g. a bin/category that only
    contains rows from a single unit), which would otherwise make linregress
    raise.
    """
    x = np.asarray(x, dtype=float)
    x_check = x[x <= spi_regression_max] if spi_regression_max is not None else x
    if len(x_check) < 2 or np.unique(x_check).size < 2:
        return np.nan
    slope, _, _, _, _, x_used = linregress_with_spi_cap(x, y, spi_regression_max)
    if len(x_used) < 2:
        return np.nan
    return slope


def compute_bin_stats(binned, spi_regression_max=None):
    """Compute slope and frac_pos for every (bin, category).

    Args:
        binned: DataFrame with 'nf_bin', 'solid_preference_index', 'p_value',
            and 'isochromatic_preference_index' columns.
        spi_regression_max: Optional SPI cap passed to the regression.

    Returns:
        Dict mapping (bin_idx, category) -> {'slope', 'frac_pos', 'n'}.
        bin_idx is the positional index into binned['nf_bin'].cat.categories.
    """
    cats = categorize_points(binned["solid_preference_index"].values,
                             binned["p_value"].values)
    binned = binned.assign(_cat=cats)
    intervals = list(binned["nf_bin"].cat.categories)

    out = {}
    for b_idx, interval in enumerate(intervals):
        bin_data = binned[binned["nf_bin"] == interval]
        for category in CATEGORIES:
            sub = bin_data if category == "All" else bin_data[bin_data["_cat"] == category]
            x = sub["solid_preference_index"].values
            y = sub["isochromatic_preference_index"].values
            slope = _fit_slope(x, y, spi_regression_max)
            frac_pos = float(np.mean(y > 0)) if len(y) else np.nan
            out[(b_idx, category)] = {"slope": slope, "frac_pos": frac_pos, "n": len(sub)}
    return out


def _bin_labels(binned):
    """Return human-readable labels for each bin index."""
    intervals = list(binned["nf_bin"].cat.categories)
    return {i: f"[{iv.left:.2f}, {iv.right:.2f}]" for i, iv in enumerate(intervals)}


# ---------------------------------------------------------------------------
# Permutation machinery
# ---------------------------------------------------------------------------
def _one_sided_p_greater(observed, null_values):
    """p-value for observed >= null (right tail), with the +1 correction.

    NaNs in null_values are ignored. Returns NaN if observed is NaN or there are
    no finite null values.
    """
    if not np.isfinite(observed):
        return np.nan
    null_values = np.asarray(null_values, dtype=float)
    null_values = null_values[np.isfinite(null_values)]
    if null_values.size == 0:
        return np.nan
    n_ge = int(np.sum(null_values >= observed))
    return (1 + n_ge) / (null_values.size + 1)


def _collect_null(stat_dicts, bin_idx, category, key):
    """Pull a list of one statistic across permutations for a (bin, category)."""
    return np.array([d.get((bin_idx, category), {}).get(key, np.nan) for d in stat_dicts],
                    dtype=float)


def _heterogeneity(stat_dict, category, key, bin_indices):
    """Between-bin spread (std) of a statistic across bins for one category."""
    vals = np.array([stat_dict.get((b, category), {}).get(key, np.nan) for b in bin_indices],
                    dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size < 2:
        return np.nan
    return float(np.std(vals))


def permutation_test_scramble_rf(data, n_perms=1000, spi_regression_max=None,
                                 n_bins=4, bin_edges=None, seed=0):
    """Permutation test that scrambles RF size across units.

    Tests, per normalized-frequency bin and per significance category:
        1) whether the ICI~SPI slope exceeds the scrambled-RF null, and
        2) whether the fraction of points with ICI > 0 exceeds the null;
    and, as the principled test of RF dependence, whether the between-bin spread
    of each statistic exceeds the null.

    Returns a dict with 'observed' (stat dict), 'bin_labels', and 'results'
    (a DataFrame of per-(bin, category) p-values) plus 'heterogeneity'
    (a DataFrame of per-category between-bin spread p-values).
    """
    rng = np.random.default_rng(seed)
    data = add_unit_key(data)

    observed_binned = compute_normfreq_bins_quiet(data, n_bins, bin_edges)
    if observed_binned is None:
        print("scramble_rf: could not bin observed data")
        return None
    observed = compute_bin_stats(observed_binned, spi_regression_max)
    bin_labels = _bin_labels(observed_binned)
    bin_indices = sorted({b for (b, _c) in observed})

    # Unit-level RF radii to shuffle (only units that have a valid radius take part;
    # units without a radius are excluded from binning in both observed and null).
    units = data.drop_duplicates("unit_key")[["unit_key", "rf_radius"]]
    valid_units = units[units["rf_radius"].notna() & (units["rf_radius"] > 0)]
    radii = valid_units["rf_radius"].to_numpy()
    valid_keys = valid_units["unit_key"].to_numpy()

    null_stats = []
    for _ in range(n_perms):
        shuffled = rng.permutation(radii)
        unit_to_radius = dict(zip(valid_keys, shuffled))
        d = data.copy()
        # Keep only units that took part, then reassign their (shuffled) radius.
        d = d[d["unit_key"].isin(valid_keys)].copy()
        d["rf_radius"] = d["unit_key"].map(unit_to_radius)
        binned = compute_normfreq_bins_quiet(d, n_bins, bin_edges)
        if binned is None:
            continue
        null_stats.append(compute_bin_stats(binned, spi_regression_max))

    results = _build_results_table(observed, null_stats, bin_indices, bin_labels)
    heterogeneity = _build_heterogeneity_table(observed, null_stats, bin_indices)
    return {"observed": observed, "bin_labels": bin_labels, "results": results,
            "heterogeneity": heterogeneity, "null_stats": null_stats,
            "bin_indices": bin_indices}


def permutation_test_scramble_spi(data, n_perms=1000, spi_regression_max=None,
                                  n_bins=4, bin_edges=None, seed=0):
    """Permutation test that scrambles (SPI, p_value) across units.

    The normalized-frequency bins are held fixed (RF unchanged); each permutation
    reassigns the unit-level (SPI, p_value) pair, breaking the SPI-ICI pairing
    and the significance-category assignment. Tests, per bin and per category:
        1) whether the ICI~SPI slope exceeds the null, and
        2) whether the fraction of points with ICI > 0 exceeds the null.

    Note: for category 'All' the ICI values in a bin are unchanged by SPI
    shuffling, so its 'frac_pos' null is degenerate (p ~ 1) and is not
    interpretable; the per-category frac_pos values are the meaningful ones.

    Returns the same structure as ``permutation_test_scramble_rf`` (without a
    heterogeneity table, which is specific to the RF test).
    """
    rng = np.random.default_rng(seed)
    data = add_unit_key(data)

    observed_binned = compute_normfreq_bins_quiet(data, n_bins, bin_edges)
    if observed_binned is None:
        print("scramble_spi: could not bin observed data")
        return None
    observed = compute_bin_stats(observed_binned, spi_regression_max)
    bin_labels = _bin_labels(observed_binned)
    bin_indices = sorted({b for (b, _c) in observed})

    # Unit-level (SPI, p_value) pairs to shuffle.
    units = observed_binned.drop_duplicates("unit_key")[
        ["unit_key", "solid_preference_index", "p_value"]]
    keys = units["unit_key"].to_numpy()
    spi = units["solid_preference_index"].to_numpy()
    pval = units["p_value"].to_numpy()

    null_stats = []
    for _ in range(n_perms):
        order = rng.permutation(len(keys))
        unit_to_spi = dict(zip(keys, spi[order]))
        unit_to_p = dict(zip(keys, pval[order]))
        d = observed_binned.copy()
        d["solid_preference_index"] = d["unit_key"].map(unit_to_spi)
        d["p_value"] = d["unit_key"].map(unit_to_p)
        null_stats.append(compute_bin_stats(d, spi_regression_max))

    results = _build_results_table(observed, null_stats, bin_indices, bin_labels)
    return {"observed": observed, "bin_labels": bin_labels, "results": results,
            "null_stats": null_stats, "bin_indices": bin_indices}


def _build_results_table(observed, null_stats, bin_indices, bin_labels):
    """Assemble a tidy DataFrame of per-(bin, category) observed values and p-values."""
    rows = []
    for b_idx in bin_indices:
        for category in CATEGORIES:
            obs = observed.get((b_idx, category), {})
            slope_obs = obs.get("slope", np.nan)
            frac_obs = obs.get("frac_pos", np.nan)
            n = obs.get("n", 0)
            slope_p = _one_sided_p_greater(slope_obs,
                                           _collect_null(null_stats, b_idx, category, "slope"))
            frac_p = _one_sided_p_greater(frac_obs,
                                          _collect_null(null_stats, b_idx, category, "frac_pos"))
            rows.append({
                "bin_idx": b_idx,
                "bin": bin_labels.get(b_idx, str(b_idx)),
                "category": category,
                "n": n,
                "slope": slope_obs,
                "slope_p_greater": slope_p,
                "frac_pos": frac_obs,
                "frac_pos_p_greater": frac_p,
            })
    return pd.DataFrame(rows)


def _build_heterogeneity_table(observed, null_stats, bin_indices):
    """Between-bin spread (std across bins) of slope and frac_pos, per category."""
    rows = []
    for category in CATEGORIES:
        slope_obs = _heterogeneity(observed, category, "slope", bin_indices)
        frac_obs = _heterogeneity(observed, category, "frac_pos", bin_indices)
        slope_null = np.array([_heterogeneity(d, category, "slope", bin_indices)
                               for d in null_stats], dtype=float)
        frac_null = np.array([_heterogeneity(d, category, "frac_pos", bin_indices)
                              for d in null_stats], dtype=float)
        rows.append({
            "category": category,
            "slope_spread": slope_obs,
            "slope_spread_p_greater": _one_sided_p_greater(slope_obs, slope_null),
            "frac_pos_spread": frac_obs,
            "frac_pos_spread_p_greater": _one_sided_p_greater(frac_obs, frac_null),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def print_results(title, results, heterogeneity=None):
    """Pretty-print a permutation-test results table."""
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)
    with pd.option_context("display.max_rows", None, "display.width", 160,
                           "display.float_format", lambda v: f"{v:.3f}"):
        print(results.to_string(index=False))
    if heterogeneity is not None:
        print("\nBetween-bin heterogeneity (does the trend depend on normalized RF?):")
        with pd.option_context("display.float_format", lambda v: f"{v:.3f}"):
            print(heterogeneity.to_string(index=False))


def plot_null_distributions(test_result, statistic, title, save_path=None):
    """Grid of null-distribution histograms (rows = bins, cols = categories).

    Args:
        test_result: Output dict from a permutation_test_* function.
        statistic: 'slope' or 'frac_pos'.
        title: Figure suptitle.
        save_path: If given, save the figure there.
    """
    null_stats = test_result["null_stats"]
    observed = test_result["observed"]
    bin_indices = test_result["bin_indices"]
    bin_labels = test_result["bin_labels"]

    n_rows = len(bin_indices)
    n_cols = len(CATEGORIES)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.2 * n_cols, 2.6 * n_rows),
                             squeeze=False)
    for r, b_idx in enumerate(bin_indices):
        for c, category in enumerate(CATEGORIES):
            ax = axes[r][c]
            null_vals = _collect_null(null_stats, b_idx, category, statistic)
            null_vals = null_vals[np.isfinite(null_vals)]
            obs = observed.get((b_idx, category), {}).get(statistic, np.nan)
            if null_vals.size:
                ax.hist(null_vals, bins=30, color="lightgray", edgecolor="gray")
            if np.isfinite(obs):
                p = _one_sided_p_greater(obs, null_vals)
                ax.axvline(obs, color="red", linewidth=2)
                ax.set_title(f"p={p:.3f}" if np.isfinite(p) else "p=n/a", fontsize=8)
            if r == 0:
                ax.annotate(category, xy=(0.5, 1.25), xycoords="axes fraction",
                            ha="center", fontsize=10, fontweight="bold")
            if c == 0:
                ax.set_ylabel(f"bin {b_idx + 1}\n{bin_labels.get(b_idx, '')}", fontsize=8)
            ax.tick_params(labelsize=7)
    fig.suptitle(f"{title}\nnull = gray histogram, observed = red line ({statistic})",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches="tight")
        print(f"Saved: {save_path}")


# ---------------------------------------------------------------------------
# Plotting the binned scatter (corrected labels)
# ---------------------------------------------------------------------------
def plot_normalized_frequency_binned(data, save_dir=None, threshold=0.7,
                                     spi_regression_max=None, n_bins=4, bin_edges=None):
    """One SPI-vs-ICI scatter per normalized-frequency bin (corrected labels)."""
    binned = compute_normfreq_bins_quiet(data, n_bins, bin_edges)
    if binned is None:
        print("No data with valid RF radius for normalized-frequency plots")
        return
    intervals = list(binned["nf_bin"].cat.categories)
    nf_cmap = plt.cm.viridis

    for b_idx, interval in enumerate(intervals):
        bin_data = binned[binned["nf_bin"] == interval]
        if bin_data.empty:
            continue
        x = bin_data["solid_preference_index"].values
        y = bin_data["isochromatic_preference_index"].values
        p_values = bin_data["p_value"].values
        nf_values = bin_data["normalized_frequency"].values
        nf_norm = plt.Normalize(vmin=float(np.min(nf_values)), vmax=float(np.max(nf_values)))

        slope, intercept, r_value, p_value, r_squared, _ = linregress_with_spi_cap(
            x, y, spi_regression_max)

        plt.figure(figsize=(11, 8))
        for i in range(len(x)):
            color = nf_cmap(nf_norm(nf_values[i]))
            if pd.notna(p_values[i]) and p_values[i] < 0.05:
                alpha_val, edge_color, lw = 0.7, "black", 0.5
            else:
                alpha_val, edge_color, lw = 0.15, "gray", 0.3
            plt.scatter(x[i], y[i], alpha=alpha_val, s=100, color=color, marker="o",
                        edgecolors=edge_color, linewidths=lw)

        _plot_category_lines(plt.gca(), x, y, p_values, spi_regression_max)

        n_significant = int(np.sum((pd.notna(p_values)) & (p_values < 0.05)))
        plt.xlabel("Solid Preference Index", fontsize=14)
        plt.ylabel("Isochromatic Preference Index", fontsize=14)
        plt.title(
            f"Solid vs Isochromatic Preference by {NORMFREQ_LABEL}\n"
            f"Bin {b_idx + 1}/{len(intervals)}: in [{interval.left:.2f}, {interval.right:.2f}] "
            f"(≥{threshold * 100:.0f}% of max)\n"
            f"(n={len(bin_data)} data points, {n_significant} solid-pref significant)",
            fontsize=13)
        add_plot_formatting(plt.gca(), r_squared, r_value, p_value, len(bin_data), n_significant)
        if plt.gca().get_legend_handles_labels()[0]:
            plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", title="Regression")
        sm = plt.cm.ScalarMappable(norm=nf_norm, cmap=nf_cmap)
        sm.set_array([])
        plt.colorbar(sm, ax=plt.gca(), orientation="horizontal", fraction=0.046, pad=0.1,
                     label=NORMFREQ_LABEL)
        plt.tight_layout()
        if save_dir:
            path = os.path.join(save_dir, f"normfreq_bin{b_idx + 1}.png")
            plt.savefig(path, dpi=300, bbox_inches="tight")
            print(f"Saved: {path}")


def _plot_category_lines(ax, x, y, p_values, spi_regression_max):
    """Draw sig-2D / non-sig / sig-3D regression lines (corrected-label helper)."""
    x = np.asarray(x)
    y = np.asarray(y)
    categories = categorize_points(x, p_values)
    for label, color in REGRESSION_CATEGORIES:
        mask = categories == label
        slope, intercept, r_value, _, r_squared, x_used = linregress_with_spi_cap(
            x[mask], y[mask], spi_regression_max)
        if len(x_used) > 1:
            line_x = np.linspace(x_used.min(), x_used.max(), 100)
            ax.plot(line_x, slope * line_x + intercept, color=color, linewidth=2.5,
                    label=f"{label} (R²={r_squared:.2f}, n={len(x_used)})")


# ---------------------------------------------------------------------------
# Top-level driver
# ---------------------------------------------------------------------------
def run(save_dir=None, threshold=0.7, filter_type="cluster", spi_regression_max=None,
        n_bins=4, bin_edges=None, n_perms=1000, seed=0, show=True):
    """Load data (same filtering as the original), plot binned scatters, and run both tests."""
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)

    merged = load_and_filter_data(threshold, filter_type=filter_type)
    if merged is None:
        print("No data available")
        return None
    data = merged["all_strong"]
    if data.empty:
        print("No 'all_strong' data available")
        return None

    # Binned scatter plots with corrected labels.
    plot_normalized_frequency_binned(data, save_dir, threshold, spi_regression_max,
                                     n_bins, bin_edges)

    # Permutation test 1: scramble RF size (tests dependence on normalized RF).
    rf_result = permutation_test_scramble_rf(
        data, n_perms=n_perms, spi_regression_max=spi_regression_max,
        n_bins=n_bins, bin_edges=bin_edges, seed=seed)
    if rf_result is not None:
        print_results("PERMUTATION TEST 1 - scramble RF size "
                      "(null for 'trend depends on normalized RF')",
                      rf_result["results"], rf_result["heterogeneity"])
        plot_null_distributions(
            rf_result, "slope", "Scramble RF size: ICI~SPI slope",
            os.path.join(save_dir, "perm_rf_slope.png") if save_dir else None)
        plot_null_distributions(
            rf_result, "frac_pos", "Scramble RF size: fraction ICI > 0",
            os.path.join(save_dir, "perm_rf_fracpos.png") if save_dir else None)

    # Permutation test 2: scramble SPI (tests whether SPI affects ICI).
    spi_result = permutation_test_scramble_spi(
        data, n_perms=n_perms, spi_regression_max=spi_regression_max,
        n_bins=n_bins, bin_edges=bin_edges, seed=seed)
    if spi_result is not None:
        print_results("PERMUTATION TEST 2 - scramble SPI "
                      "(null for 'SPI has an effect on ICI')",
                      spi_result["results"])
        plot_null_distributions(
            spi_result, "slope", "Scramble SPI: ICI~SPI slope",
            os.path.join(save_dir, "perm_spi_slope.png") if save_dir else None)
        plot_null_distributions(
            spi_result, "frac_pos", "Scramble SPI: fraction ICI > 0",
            os.path.join(save_dir, "perm_spi_fracpos.png") if save_dir else None)

    if show:
        plt.show()
    return {"rf": rf_result, "spi": spi_result}


if __name__ == "__main__":
    run(
        save_dir="/home/connorlab/Documents/plots/spi_vs_ici_normfreq_permutation",
        threshold=0.70,
        filter_type="cluster",
        spi_regression_max=0.5,
        bin_edges=[0, 1.5, 2.5, 8.0, np.inf],
        n_perms=1000,
        seed=0,
    )

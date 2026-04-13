"""
rwa_prediction.py
-----------------
General-use utilities for computing RWA-predicted responses and plotting
real vs predicted scatter plots.

Prediction logic:
    For each stimulus, look up the RWA matrix value at the bin position of
    every component (shaft, termination, or junction) and average across
    components.  This gives one predicted scalar per stimulus.

Typical usage in plot_rwa.py:
    from src.analysis.ga.rwa_prediction import compute_predictions, plot_real_vs_predicted
    preds = compute_predictions(shaft_rwa, data["Shaft"])
    plot_real_vs_predicted(data["Response-1"], preds, title="Shaft", ax=ax)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.stats import linregress

from src.analysis.ga.rwa import RWAMatrix, get_point_indices


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OTHER_LABEL = "Other"
OTHER_COLOR = "#aaaaaa"

# Cycle through these markers when symbol_by is set.
MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X', 'h', '*', 'p', '8', '<', '>']


# ---------------------------------------------------------------------------
# Group / filter helpers
# ---------------------------------------------------------------------------

def limit_groups_to_top_n(groups, n: int, other_label: str = OTHER_LABEL) -> pd.Series:
    """
    Replace every group that isn't in the top-n (by count) with *other_label*.

    Args:
        groups:       Iterable of group labels (e.g. lineage IDs).
        n:            How many groups to keep individually.
        other_label:  Label assigned to all remaining groups.

    Returns:
        pandas Series with the same index, top-n kept, rest → other_label.
    """
    s = pd.Series(groups).reset_index(drop=True)
    top = set(s.value_counts().nlargest(n).index)
    return s.where(s.isin(top), other=other_label)


def apply_filters(
        data: pd.DataFrame,
        filters: dict,
        mode: str = "include",
) -> pd.DataFrame:
    """
    Filter rows of *data* by column-value matching.

    Args:
        data:    DataFrame to filter.
        filters: Mapping of column name → scalar or list[scalar].
                 A row *matches* when, for every column in *filters*, the
                 row's value is contained in the corresponding value list.
        mode:    ``"include"`` — keep only rows that match all filters.
                 ``"exclude"`` — drop rows that match all filters.

    Returns:
        Filtered DataFrame with the original index preserved.

    Examples::

        # keep only lineages 1 and 2
        apply_filters(data, {"Lineage": [1, 2]}, mode="include")

        # drop generation 0 catch trials
        apply_filters(data, {"GenId": 0}, mode="exclude")

        # keep specific lineages AND specific generations
        apply_filters(data, {"Lineage": [1, 2], "GenId": [3, 4, 5]})
    """
    if not filters:
        return data
    mask = pd.Series(True, index=data.index)
    for col, values in filters.items():
        if col not in data.columns:
            print(f"Warning: filter column '{col}' not found — skipping.")
            continue
        if not isinstance(values, list):
            values = [values]
        mask &= data[col].isin(values)
    if mode == "exclude":
        mask = ~mask
    return data[mask]


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def predict_response_from_rwa(rwa_matrix: RWAMatrix, stim) -> float:
    """
    Predict the response for a single stimulus by looking up the RWA matrix
    at the bin position of each component and averaging.

    Args:
        rwa_matrix: The RWAMatrix used for prediction.
        stim:       A single stimulus — dict (one component) or list[dict]
                    (multi-component, e.g. multiple shafts).

    Returns:
        Mean RWA value across all binnable components.  NaN if nothing bins.
    """
    if stim is None:
        return np.nan

    # Normalise to list; filter out any None components
    if not isinstance(stim, list):
        stim = [stim]
    stim = [c for c in stim if c is not None]
    if not stim:
        return np.nan

    indices_per_component = get_point_indices(rwa_matrix, stim)
    values = []
    for component_indices in indices_per_component:
        if component_indices is None or None in component_indices:
            continue
        try:
            values.append(float(rwa_matrix.matrix[tuple(component_indices)]))
        except IndexError:
            continue
    return float(np.mean(values)) if values else np.nan


def compute_predictions(rwa_matrix: RWAMatrix, stim_series) -> np.ndarray:
    """
    Compute predicted responses for every stimulus in a pandas Series.

    Args:
        rwa_matrix:  The RWAMatrix used for prediction.
        stim_series: pandas Series; each element is a stim (dict or list[dict]).

    Returns:
        numpy array of predicted responses (NaN where binning fails).
    """
    return np.array([predict_response_from_rwa(rwa_matrix, s) for s in stim_series])


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_real_vs_predicted(
        real_responses,
        predicted_responses,
        title: str = "Real vs Predicted",
        ax: Optional[plt.Axes] = None,
        color: str = 'steelblue',
) -> plt.Axes:
    """
    Scatter plot of real (measured) vs RWA-predicted responses.

    Annotates with Pearson r, p-value, a regression line, and a y=x
    identity line.  NaN/Inf pairs are silently dropped.

    Args:
        real_responses:      Iterable of measured responses.
        predicted_responses: Iterable of RWA-predicted responses.
        title:               Axes title.
        ax:                  Existing Axes to draw into; creates one if None.
        color:               Scatter dot colour.

    Returns:
        The matplotlib Axes.
    """
    return plot_real_vs_predicted_grouped(
        real_responses, predicted_responses,
        groups=None, title=title, ax=ax,
        single_color=color,
    )


def plot_real_vs_predicted_grouped(
        real_responses,
        predicted_responses,
        groups=None,
        symbols=None,
        title: str = "Real vs Predicted",
        ax: Optional[plt.Axes] = None,
        group_label: str = "Group",
        symbol_label: str = "Symbol",
        single_color: str = 'steelblue',
        cmap_name: str = 'tab20',
) -> plt.Axes:
    """
    Scatter plot of real vs RWA-predicted responses, with optional
    per-group colouring and/or per-group marker symbols.

    Both *groups* and *symbols* can be active at the same time, letting you
    compare two independent conditions simultaneously (e.g. colour = lineage,
    symbol = stim type).

    Args:
        real_responses:      Iterable of measured responses.
        predicted_responses: Iterable of RWA-predicted responses.
        groups:              Optional iterable of colour-group labels.
                             ``None`` → all dots share *single_color*.
        symbols:             Optional iterable of symbol-group labels.
                             ``None`` → all dots use circle markers.
        title:               Axes title.
        ax:                  Existing Axes; creates one if None.
        group_label:         Legend title for the colour grouping.
        symbol_label:        Legend title for the symbol grouping.
        single_color:        Dot colour when *groups* is None.
        cmap_name:           Matplotlib colormap for group colours.

    Returns:
        The matplotlib Axes.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))

    real = np.asarray(real_responses, dtype=float)
    pred = np.asarray(predicted_responses, dtype=float)
    grps = np.asarray(groups) if groups is not None else None
    syms = np.asarray(symbols) if symbols is not None else None

    mask = np.isfinite(real) & np.isfinite(pred)
    real, pred = real[mask], pred[mask]
    if grps is not None:
        grps = grps[mask]
    if syms is not None:
        syms = syms[mask]

    # ── build colour map ─────────────────────────────────────────────────────
    if grps is not None:
        named = sorted(g for g in set(grps) if g != OTHER_LABEL)
        color_order = named + ([OTHER_LABEL] if OTHER_LABEL in set(grps) else [])
        cmap = plt.get_cmap(cmap_name)
        n = max(len(named) - 1, 1)
        colors = {g: cmap(i / n) for i, g in enumerate(named)}
        colors[OTHER_LABEL] = OTHER_COLOR
    else:
        color_order = [None]
        colors = {None: single_color}

    # ── build marker map ─────────────────────────────────────────────────────
    if syms is not None:
        sym_order = sorted(set(syms), key=str)
        marker_map = {s: MARKERS[i % len(MARKERS)] for i, s in enumerate(sym_order)}
    else:
        sym_order = [None]
        marker_map = {None: 'o'}

    # ── scatter ──────────────────────────────────────────────────────────────
    for g in color_order:
        for s in sym_order:
            gm = (grps == g) if g is not None else np.ones(len(real), dtype=bool)
            sm = (syms == s) if s is not None else np.ones(len(real), dtype=bool)
            m = gm & sm
            if not m.any():
                continue
            is_other = (g == OTHER_LABEL)
            ax.scatter(real[m], pred[m],
                       alpha=0.25 if is_other else 0.7,
                       s=40,
                       color=colors[g],
                       marker=marker_map[s],
                       edgecolors='none',
                       zorder=1 if is_other else 2)

    # ── legends ──────────────────────────────────────────────────────────────
    if grps is not None:
        color_handles = [mpatches.Patch(color=colors[g], label=str(g))
                         for g in color_order]
        ncol = max(1, len(color_order) // 12)
        leg1 = ax.legend(handles=color_handles, title=group_label, fontsize=7,
                         title_fontsize=8, ncol=ncol, loc='upper left')
        if syms is not None:
            sym_handles = [Line2D([0], [0], marker=marker_map[s], color='#555555',
                                   linestyle='none', markersize=7, label=str(s))
                           for s in sym_order]
            ax.add_artist(leg1)
            ax.legend(handles=sym_handles, title=symbol_label, fontsize=7,
                      title_fontsize=8, loc='lower right')
    elif syms is not None:
        sym_handles = [Line2D([0], [0], marker=marker_map[s], color=single_color,
                               linestyle='none', markersize=7, label=str(s))
                       for s in sym_order]
        ax.legend(handles=sym_handles, title=symbol_label, fontsize=7,
                  title_fontsize=8, loc='upper left')

    # ── regression + annotation ──────────────────────────────────────────────
    if len(real) >= 2:
        slope, intercept, r, p, _ = linregress(real, pred)
        x_fit = np.linspace(real.min(), real.max(), 200)
        p_label = f"p={p:.3f}" if p >= 0.001 else "p<0.001"
        ax.plot(x_fit, slope * x_fit + intercept,
                color='crimson', linewidth=1.5, linestyle='--', zorder=5)
        ax.annotate(f"r={r:.2f}, {p_label}",
                    xy=(0.97, 0.05), xycoords='axes fraction',
                    ha='right', fontsize=9, color='crimson')

    # ── y = x ────────────────────────────────────────────────────────────────
    if len(real):
        lo = min(real.min(), pred.min())
        hi = max(real.max(), pred.max())
        ax.plot([lo, hi], [lo, hi], 'k-', linewidth=0.8, alpha=0.3)

    ax.set_xlabel("Real Response", fontsize=10)
    ax.set_ylabel("Predicted (RWA)", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight='bold')

    return ax

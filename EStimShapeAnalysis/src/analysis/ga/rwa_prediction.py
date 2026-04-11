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
import matplotlib.pyplot as plt
from scipy.stats import linregress

from src.analysis.ga.rwa import RWAMatrix, get_point_indices


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
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))

    real = np.asarray(real_responses, dtype=float)
    pred = np.asarray(predicted_responses, dtype=float)

    mask = np.isfinite(real) & np.isfinite(pred)
    real, pred = real[mask], pred[mask]

    ax.scatter(real, pred, alpha=0.6, s=40, color=color, edgecolors='none')

    if len(real) >= 2:
        slope, intercept, r, p, _ = linregress(real, pred)
        x_fit = np.linspace(real.min(), real.max(), 200)
        p_label = f"p={p:.3f}" if p >= 0.001 else "p<0.001"
        ax.plot(x_fit, slope * x_fit + intercept,
                color='crimson', linewidth=1.5,
                label=f"r={r:.2f}, {p_label}")

    if len(real):
        lo = min(real.min(), pred.min())
        hi = max(real.max(), pred.max())
        ax.plot([lo, hi], [lo, hi], 'k--', linewidth=1, alpha=0.4, label='y = x')

    ax.set_xlabel("Real Response", fontsize=10)
    ax.set_ylabel("Predicted (RWA)", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)

    return ax

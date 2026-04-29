from __future__ import annotations

import ast
import os
from typing import Optional, Union

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.patches import Ellipse
from scipy.stats import chi2


class ReceptiveFieldFilter:
    """
    Filter stimuli whose center of mass lies outside the estimated receptive field.

    The RF is approximated as a 2D Gaussian ellipse defined by the
    response-weighted mean and covariance of all stimulus mass-center positions
    (the ``MassCenter`` column).  Stimuli whose Mahalanobis distance from the RF
    center exceeds ``mahal_cutoff`` are removed from the dataframe.

    Default cutoff = sqrt(chi2.ppf(0.95, df=2)) ≈ 2.45, corresponding to the
    95th-percentile ellipse of the response-weighted distribution.

    This class is reusable: it does not depend on axis-coding specifics; it only
    requires a ``MassCenter`` column and access to a per-trial response column.
    """

    def __init__(
        self,
        mahal_cutoff: Optional[float] = None,
        plot: bool = True,
        save_dir: Optional[str] = None,
    ):
        self.mahal_cutoff = (
            float(np.sqrt(chi2.ppf(0.95, df=2)))
            if mahal_cutoff is None
            else float(mahal_cutoff)
        )
        self.plot = plot
        self.save_dir = save_dir

        # Populated after fit_and_filter():
        self.rf_center_: Optional[np.ndarray] = None
        self.rf_cov_: Optional[np.ndarray] = None
        self.positions_: Optional[np.ndarray] = None
        self.responses_: Optional[np.ndarray] = None
        self.accepted_mask_: Optional[np.ndarray] = None
        self.mahal_distances_: Optional[np.ndarray] = None

    def fit_and_filter(
        self,
        df: pd.DataFrame,
        channel: Union[str, list[str]],
        spike_rates_col: Optional[str],
    ) -> pd.DataFrame:
        """
        Parse MassCenter, estimate the RF, and return a copy of ``df`` with
        trials belonging to out-of-RF stimuli removed.

        Parameters
        ----------
        df
            Trial-level dataframe with ``StimSpecId`` and ``MassCenter`` columns.
        channel
            Same convention as ``AxisCodingDataset``:
            "GA" → use ``GA Response``; str/list → use ``spike_rates_col``.
        spike_rates_col
            Name of the per-trial spike-rate dict column (None when channel="GA").
        """
        from src.analysis.ga.axis_coding.axis_coding_dataset import (
            _extract_per_trial_response,
        )

        if "MassCenter" not in df.columns:
            print("[rf_filter] 'MassCenter' column not found; skipping RF filter.")
            return df

        df = df.copy()
        df["_rf_x"] = df["MassCenter"].apply(lambda v: _parse_mass_center_coord(v, 0))
        df["_rf_y"] = df["MassCenter"].apply(lambda v: _parse_mass_center_coord(v, 1))
        df["_rf_resp"] = _extract_per_trial_response(df, channel, spike_rates_col)

        # Per-stimulus: first mass-center occurrence (stimulus property, not trial)
        # and mean response across trials.
        per_stim = (
            df.groupby("StimSpecId")
            .agg(
                x=("_rf_x", "first"),
                y=("_rf_y", "first"),
                resp=("_rf_resp", "mean"),
            )
            .dropna()
        )

        if len(per_stim) == 0:
            print("[rf_filter] No valid MassCenter data; skipping RF filter.")
            return df.drop(columns=["_rf_x", "_rf_y", "_rf_resp"], errors="ignore")

        xy = per_stim[["x", "y"]].values.astype(np.float64)   # (n_stim, 2)
        resp = per_stim["resp"].values.astype(np.float64)

        # Response-weighted mean and covariance.
        w = np.clip(resp, 0.0, None)
        w_sum = float(w.sum())
        w = w / w_sum if w_sum > 1e-12 else np.ones(len(resp)) / len(resp)

        mu = (w[:, None] * xy).sum(axis=0)
        delta = xy - mu
        cov = (w[:, None] * delta).T @ delta
        cov += np.eye(2) * 1e-6  # regularize against singularity

        try:
            cov_inv = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            cov_inv = np.eye(2)

        # Mahalanobis distance per stimulus.
        mahal = np.sqrt(np.einsum("ij,jk,ik->i", delta, cov_inv, delta))
        accepted = mahal <= self.mahal_cutoff

        self.rf_center_ = mu
        self.rf_cov_ = cov
        self.positions_ = xy
        self.responses_ = resp
        self.accepted_mask_ = accepted
        self.mahal_distances_ = mahal

        n_acc = int(accepted.sum())
        n_total = len(per_stim)
        print(
            f"[rf_filter] accepted {n_acc}/{n_total} stimuli "
            f"(Mahalanobis ≤ {self.mahal_cutoff:.2f}; "
            f"{n_total - n_acc} rejected)"
        )

        if self.plot:
            fig = self._make_plot()
            if self.save_dir is not None:
                os.makedirs(self.save_dir, exist_ok=True)
                path = os.path.join(self.save_dir, "rf_filter.png")
                fig.savefig(path, dpi=150, bbox_inches="tight")
                print(f"[rf_filter] saved: {path}")
            plt.show()

        accepted_ids = set(per_stim.index[accepted])
        df = df[df["StimSpecId"].isin(accepted_ids)]
        return df.drop(columns=["_rf_x", "_rf_y", "_rf_resp"], errors="ignore")

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------

    def _make_plot(self) -> plt.Figure:
        xy = self.positions_
        resp = self.responses_
        accepted = self.accepted_mask_
        mu = self.rf_center_
        cov = self.rf_cov_
        mahal = self.mahal_distances_

        fig, axes = plt.subplots(1, 2, figsize=(13, 5))

        # Panel 1: spatial distribution
        ax = axes[0]
        ax.scatter(
            xy[accepted, 0], xy[accepted, 1],
            c="steelblue", s=30, alpha=0.7,
            label=f"accepted ({accepted.sum()})",
        )
        if (~accepted).any():
            ax.scatter(
                xy[~accepted, 0], xy[~accepted, 1],
                c="crimson", s=30, alpha=0.7, marker="x",
                label=f"rejected ({(~accepted).sum()})",
            )
        ax.scatter(mu[0], mu[1], c="gold", s=120, zorder=6, marker="*", label="RF center")
        _draw_mahal_ellipse(
            ax, mu, cov, self.mahal_cutoff,
            color="black", lw=1.5, label=f"cutoff = {self.mahal_cutoff:.2f}",
        )
        ax.set_xlabel("Mass center X (deg)")
        ax.set_ylabel("Mass center Y (deg)")
        ax.set_title("RF filter: mass center distribution")
        ax.legend(fontsize=8)
        ax.set_aspect("equal", adjustable="datalim")

        # Panel 2: Mahalanobis distance vs mean response
        ax = axes[1]
        ax.scatter(
            mahal[accepted], resp[accepted],
            c="steelblue", s=20, alpha=0.7, label="accepted",
        )
        if (~accepted).any():
            ax.scatter(
                mahal[~accepted], resp[~accepted],
                c="crimson", s=20, alpha=0.7, marker="x", label="rejected",
            )
        ax.axvline(
            self.mahal_cutoff, color="black", lw=1.5, ls="--",
            label=f"cutoff = {self.mahal_cutoff:.2f}",
        )
        ax.set_xlabel("Mahalanobis distance from RF center")
        ax.set_ylabel("Mean response")
        ax.set_title("Response vs RF distance")
        ax.legend(fontsize=8)

        fig.tight_layout()
        return fig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_mass_center_coord(value, idx: int) -> Optional[float]:
    """
    Extract coordinate at ``idx`` from a MassCenter cell.

    The value may be a Python string representation of a tuple, an actual
    tuple, or a list. Only the first two elements are meaningful (x, y);
    z is always ≈ 0 and is ignored.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return None
    if isinstance(value, (tuple, list)) and len(value) > idx:
        try:
            return float(value[idx])
        except (ValueError, TypeError):
            return None
    return None


def _draw_mahal_ellipse(ax, mu, cov: np.ndarray, n_std: float, **kwargs):
    """
    Overlay the Mahalanobis ellipse at ``n_std`` on ``ax``.

    Keyword arguments are forwarded to both the Ellipse patch (minus ``label``)
    and a dummy line plot (for the legend).
    """
    vals, vecs = np.linalg.eigh(cov)
    vals = np.clip(vals, 0.0, None)
    # Major axis: last eigenvector (largest eigenvalue after eigh ascending sort).
    angle_deg = float(np.degrees(np.arctan2(float(vecs[1, -1]), float(vecs[0, -1]))))
    width = float(2.0 * n_std * np.sqrt(vals[-1]))
    height = float(2.0 * n_std * np.sqrt(vals[0]))

    label = kwargs.pop("label", None)
    ellipse = Ellipse(
        xy=(float(mu[0]), float(mu[1])),
        width=width,
        height=height,
        angle=angle_deg,
        fill=False,
        **kwargs,
    )
    ax.add_patch(ellipse)
    if label is not None:
        ax.plot([], [], label=label, **kwargs)

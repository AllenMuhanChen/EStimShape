"""
Visualize how object-centered position varies along the preferred axis (and the
top-N orthogonal axes) of a saved axis-coding model.

Reads the JSONs that ``fit_axis_coding`` writes (``axis_coding_*.json``), pulls
the per-stim projections + selected component indices out of them, reloads the
original df from the repository (NO model refit), and produces one PNG per JSON
showing how the selected component's object-centered position
(``radialPosition``, ``angularPosition.theta``, ``angularPosition.phi``, plus
the encoded Cartesian ``x, y, z``) varies as a function of axis projection.

Hypothesis the plots address: stimuli closer to the positive end of a neuron's
preferred axis should have a chosen component closer to the neuron's preferred
location; stimuli at the negative end should be farther/elsewhere. Orthogonal
axes should show no such trend if the axis-coding result holds.

Set the variables in ``main()`` below and run the file directly.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from src.analysis.ga.axis_coding.axis_coding_dataset import (
    _coerce_to_list_of_dicts,
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _prepare_session_df(session_id: str) -> pd.DataFrame:
    """
    Switch context to ``session_id`` and return the prepared df that
    ``AxisCodingAnalysis.analyze`` operates on (post ``_prepare_dataframe`` —
    spherical-angle conditioning + 2D flattening + lineage/baseline filter).

    Uses ``import_data`` on the repository copy, so this is a fast read once
    ``compile_and_export`` has been run for the session at least once.
    """
    from src.startup.apply_session_context import apply_session_context
    from src.analysis.ga.axis_coding.axis_coding_analysis import (
        AxisCodingAnalysis,
    )

    apply_session_context(session_id)

    analysis = AxisCodingAnalysis(
        show_plots=False,
        export_to_repository=False,
        recompute=False,
    )
    analysis.session_id = session_id
    analysis.parse_data_type("raw", session_id=session_id)

    try:
        df = analysis.import_data(None)
    except Exception as exc:
        # Repository miss — fall back to a full compile_and_export, which
        # populates the repository for next time.
        print(
            f"[position_along_axis] import_from_repository failed "
            f"({exc}); running compile_and_export as fallback."
        )
        df = analysis.compile_and_export()

    return AxisCodingAnalysis._prepare_dataframe(df)


def _per_stim_components(df: pd.DataFrame, component_type: str) -> dict:
    """
    Map StimSpecId -> list[component dict] for ``component_type``, mirroring
    AxisCodingDataset.build's "first occurrence per StimSpecId" rule. Components
    arrive as either lists, single dicts, or stringified list-of-dicts, so we
    coerce uniformly.
    """
    if component_type not in df.columns:
        raise KeyError(
            f"Component column '{component_type}' missing in prepared df."
        )
    sub = df[df["StimSpecId"].notna()].copy()
    sub[component_type] = sub[component_type].apply(_coerce_to_list_of_dicts)
    first_per_stim = sub.groupby("StimSpecId")[component_type].first()
    return {sid: comps for sid, comps in first_per_stim.items() if comps}


def _build_design_matrix_for_json(
    stim_ids: list,
    selected_indices: list[int],
    components_by_stim: dict,
    component_type: str,
) -> tuple[np.ndarray, list[str]]:
    """
    Reconstruct the (n_stim, d) z-scored feature-space design matrix the
    model would have seen at fit time, in JSON ``stim_ids`` order. Same
    recipe as ``AxisCodingDataset.build`` but stripped of response/grouping
    work — encode every stim's components, fit ``StandardScaler`` on the
    union, scale, and pick the saved-selected component per stim.

    Returned in the model's ORIGINAL feature space (not PC space), even if
    the original fit used ``n_pcs > 0`` — that's what the JSON's
    ``feature_names`` describes, and what the position/non-position split
    operates on. Stims whose component lookup fails come back as a row of
    NaN; the analysis filters those.
    """
    from src.analysis.ga.axis_coding.component_encoding import make_default_encoders

    encoder = make_default_encoders()[component_type]

    # Encode every stim's components so the scaler is fit on the same union
    # of components the original AxisCodingDataset.build would have seen.
    encoded: dict = {}
    for sid, comps in components_by_stim.items():
        encoded[sid] = encoder.encode_components(comps)

    nonempty = [arr for arr in encoded.values() if arr.shape[0] > 0]
    if not nonempty:
        return np.zeros((len(stim_ids), encoder.n_features)), list(encoder.feature_names)
    encoder.fit_scaler(np.vstack(nonempty))

    n = len(stim_ids)
    d = encoder.n_features
    X = np.full((n, d), np.nan)
    for i, sid in enumerate(stim_ids):
        comps_enc = encoded.get(sid)
        if comps_enc is None and not isinstance(sid, int):
            try:
                comps_enc = encoded.get(int(sid))
            except (TypeError, ValueError):
                comps_enc = None
        if comps_enc is None or comps_enc.shape[0] == 0:
            continue
        idx = int(selected_indices[i])
        if 0 <= idx < comps_enc.shape[0]:
            X[i] = encoder.transform_with_scaler(comps_enc)[idx]
    return X, list(encoder.feature_names)


# ---------------------------------------------------------------------------
# Per-stim position extraction
# ---------------------------------------------------------------------------

@dataclass
class PositionTable:
    """All per-stim position values aligned to the JSON's stim_ids order."""

    radial: np.ndarray              # (n_stim,)
    theta: np.ndarray               # (n_stim,) radians
    phi: np.ndarray                 # (n_stim,) radians
    xyz: np.ndarray                 # (n_stim, 3) Cartesian (radial * unit-sphere)
    valid_mask: np.ndarray          # (n_stim,) bool — True if a position was found


def _extract_positions(
    stim_ids: list,
    selected_indices: list[int],
    components_by_stim: dict,
) -> PositionTable:
    n = len(stim_ids)
    radial = np.full(n, np.nan)
    theta = np.full(n, np.nan)
    phi = np.full(n, np.nan)
    xyz = np.full((n, 3), np.nan)
    valid = np.zeros(n, dtype=bool)

    n_warn = 0
    for i, sid in enumerate(stim_ids):
        comps = components_by_stim.get(sid)
        if not comps and not isinstance(sid, int):
            try:
                comps = components_by_stim.get(int(sid))
            except (TypeError, ValueError):
                comps = None
        if not comps:
            n_warn += 1
            continue

        idx = int(selected_indices[i])
        if idx < 0 or idx >= len(comps):
            n_warn += 1
            continue

        comp = comps[idx]
        try:
            r = float(comp["radialPosition"])
            t = float(comp["angularPosition"]["theta"])
            p = float(comp["angularPosition"]["phi"])
        except (KeyError, TypeError, ValueError):
            n_warn += 1
            continue

        radial[i] = r
        theta[i] = t
        phi[i] = p
        sin_phi = np.sin(p)
        xyz[i] = r * np.array(
            [sin_phi * np.cos(t), sin_phi * np.sin(t), np.cos(p)]
        )
        valid[i] = True

    if n_warn:
        print(
            f"  [position] warning: {n_warn}/{n} stim missing component "
            f"position (selected_indices out of range or fields absent)."
        )

    return PositionTable(radial=radial, theta=theta, phi=phi, xyz=xyz, valid_mask=valid)


# ---------------------------------------------------------------------------
# Binning
# ---------------------------------------------------------------------------

@dataclass
class BinnedAxis:
    label: str
    centers: np.ndarray            # (n_bins,)
    counts: np.ndarray             # (n_bins,)
    radial_mean: np.ndarray
    radial_sem: np.ndarray
    theta_mean: np.ndarray         # circular mean
    theta_sem: np.ndarray          # circular SEM (radians)
    phi_mean: np.ndarray           # circular mean
    phi_sem: np.ndarray            # circular SEM (radians)
    xyz_mean: np.ndarray           # (n_bins, 3) Cartesian mean position
    variance: Optional[float] = None  # axis variance (for orth axes)


def _circular_mean_sem(angles: np.ndarray) -> tuple[float, float]:
    """
    Circular mean and circular SEM (radians) of a set of angles.

    SEM uses Fisher's circular standard deviation
    ``sigma = sqrt(-2 * ln(R))`` where R is the mean resultant length, then
    divides by sqrt(n). With n == 1 there is no within-bin variability,
    so SEM is 0. R == 0 (perfectly anti-aligned) -> infinite SEM, capped
    at pi for plotting.
    """
    n = angles.size
    if n == 0:
        return float("nan"), float("nan")
    mean_cos = float(np.mean(np.cos(angles)))
    mean_sin = float(np.mean(np.sin(angles)))
    mu = float(np.arctan2(mean_sin, mean_cos))
    if n == 1:
        return mu, 0.0
    R = float(np.hypot(mean_cos, mean_sin))
    R = max(min(R, 1.0), 1e-12)
    sigma = float(np.sqrt(-2.0 * np.log(R)))
    sem = float(min(sigma / np.sqrt(n), np.pi))
    return mu, sem


def _bin_axis(
    projections: np.ndarray,
    pos: PositionTable,
    label: str,
    n_bins: int,
    z_range: float,
    axis_variance: Optional[float] = None,
) -> BinnedAxis:
    """Z-score projections then bin into ``n_bins`` evenly-spaced bins in [-z, z]."""
    proj = np.asarray(projections, dtype=np.float64)
    finite = np.isfinite(proj) & pos.valid_mask
    proj = proj[finite]
    radial = pos.radial[finite]
    theta = pos.theta[finite]
    phi = pos.phi[finite]
    xyz = pos.xyz[finite]

    if proj.size == 0:
        empty = np.full(n_bins, np.nan)
        return BinnedAxis(
            label=label,
            centers=np.linspace(-z_range, z_range, n_bins),
            counts=np.zeros(n_bins, dtype=int),
            radial_mean=empty, radial_sem=empty,
            theta_mean=empty, phi_mean=empty,
            mag_mean=empty,
            xyz_mean=np.full((n_bins, 3), np.nan),
            variance=axis_variance,
        )

    proj_std = float(np.std(proj, ddof=1)) if proj.size >= 2 else 1.0
    if proj_std < 1e-12:
        proj_std = 1.0
    z = (proj - float(np.mean(proj))) / proj_std

    edges = np.linspace(-z_range, z_range, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    bin_idx = np.digitize(z, edges) - 1
    valid = (bin_idx >= 0) & (bin_idx < n_bins)

    counts = np.zeros(n_bins, dtype=int)
    radial_mean = np.full(n_bins, np.nan)
    radial_sem = np.full(n_bins, np.nan)
    theta_mean = np.full(n_bins, np.nan)
    theta_sem = np.full(n_bins, np.nan)
    phi_mean = np.full(n_bins, np.nan)
    phi_sem = np.full(n_bins, np.nan)
    xyz_mean = np.full((n_bins, 3), np.nan)

    for b in range(n_bins):
        sel = valid & (bin_idx == b)
        n_sel = int(sel.sum())
        counts[b] = n_sel
        if n_sel == 0:
            continue
        rs = radial[sel]
        radial_mean[b] = float(np.mean(rs))
        radial_sem[b] = (
            float(np.std(rs, ddof=1) / np.sqrt(n_sel)) if n_sel > 1 else 0.0
        )
        theta_mean[b], theta_sem[b] = _circular_mean_sem(theta[sel])
        phi_mean[b], phi_sem[b] = _circular_mean_sem(phi[sel])
        xyz_mean[b] = xyz[sel].mean(axis=0)

    return BinnedAxis(
        label=label,
        centers=centers,
        counts=counts,
        radial_mean=radial_mean,
        radial_sem=radial_sem,
        theta_mean=theta_mean,
        theta_sem=theta_sem,
        phi_mean=phi_mean,
        phi_sem=phi_sem,
        xyz_mean=xyz_mean,
        variance=axis_variance,
    )


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _plot_figure(
    rows: list[BinnedAxis],
    title: str,
    mu_decoded: Optional[dict],
) -> plt.Figure:
    n_rows = len(rows)
    fig, axes = plt.subplots(
        nrows=n_rows,
        ncols=4,
        figsize=(18, 3.6 * n_rows),
        squeeze=False,
        gridspec_kw={"width_ratios": [1, 1, 1, 3]},
        constrained_layout=True,
    )

    col_titles = [
        "radialPosition (mean ± SEM)",
        "angularPosition.theta (circular mean)",
        "angularPosition.phi (circular mean)",
        "mean (x, y) vector per bin  |  color = depth z   "
        "(blue = +z away, red = −z toward)",
    ]

    # Symmetric coolwarm matches the depth convention used in the μ plot
    # (axis_coding_analysis.py:2490): blue = +z (away, φ=0), red = −z
    # (toward, φ=π).
    depth_cmap = plt.cm.coolwarm

    # Global depth scale across all rows so colors are comparable. Use the
    # max |z| seen across every row's xyz_mean (so all arrows share a colorbar).
    all_z = np.concatenate(
        [b.xyz_mean[:, 2][np.isfinite(b.xyz_mean[:, 2])] for b in rows]
    )
    z_abs_max = float(np.max(np.abs(all_z))) if all_z.size else 1.0
    if z_abs_max < 1e-12:
        z_abs_max = 1.0

    for r, b in enumerate(rows):
        for c in range(4):
            ax = axes[r, c]
            if r == 0:
                ax.set_title(col_titles[c], fontsize=10)

            if c == 0:
                ax.errorbar(
                    b.centers, b.radial_mean, yerr=b.radial_sem,
                    fmt="o-", color="tab:blue", capsize=3, lw=1.2,
                )
                if mu_decoded is not None and "radialPosition" in mu_decoded:
                    ax.axhline(
                        float(mu_decoded["radialPosition"]),
                        color="grey", lw=0.8, ls="--",
                        label="μ (selector prototype)",
                    )
                    ax.legend(fontsize=7, loc="best")
                ax.set_ylabel(b.label, fontsize=10)
                ax.set_xlabel("axis projection (z)", fontsize=8)
            elif c == 1:
                ax.errorbar(
                    b.centers, b.theta_mean, yerr=b.theta_sem,
                    fmt="o-", color="tab:orange", capsize=3, lw=1.2,
                )
                if mu_decoded is not None and "angularPosition.theta" in mu_decoded:
                    ax.axhline(
                        float(mu_decoded["angularPosition.theta"]),
                        color="grey", lw=0.8, ls="--",
                    )
                ax.set_ylim(-np.pi - 0.1, np.pi + 0.1)
                ax.set_yticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
                ax.set_yticklabels(["-π", "-π/2", "0", "π/2", "π"], fontsize=7)
                ax.set_xlabel("axis projection (z)", fontsize=8)
            elif c == 2:
                ax.errorbar(
                    b.centers, b.phi_mean, yerr=b.phi_sem,
                    fmt="o-", color="tab:green", capsize=3, lw=1.2,
                )
                if mu_decoded is not None and "angularPosition.phi" in mu_decoded:
                    ax.axhline(
                        float(mu_decoded["angularPosition.phi"]),
                        color="grey", lw=0.8, ls="--",
                    )
                ax.set_ylim(-0.1, np.pi + 0.1)
                ax.set_yticks([0, np.pi / 4, np.pi / 2, 3 * np.pi / 4, np.pi])
                ax.set_yticklabels(["0", "π/4", "π/2", "3π/4", "π"], fontsize=7)
                ax.set_xlabel("axis projection (z)", fontsize=8)
            elif c == 3:
                _draw_arrow_row(
                    ax, b, depth_cmap=depth_cmap, z_abs_max=z_abs_max,
                )

            ax.tick_params(labelsize=7)
            ax.grid(alpha=0.25)

        # Per-row label on the leftmost panel includes axis variance for orth
        # axes so the reader knows which orthogonal direction this is.
        var_str = (
            f"  (var={b.variance:.3f})"
            if b.variance is not None and np.isfinite(b.variance)
            else ""
        )
        axes[r, 0].annotate(
            f"{b.label}{var_str}",
            xy=(-0.28, 0.5), xycoords="axes fraction",
            ha="right", va="center", rotation=90,
            fontsize=11, fontweight="bold",
        )

    # Shared depth colorbar on the right edge of the arrow column.
    sm = plt.cm.ScalarMappable(
        cmap=depth_cmap,
        norm=plt.Normalize(vmin=-z_abs_max, vmax=z_abs_max),
    )
    sm.set_array([])
    cbar = fig.colorbar(
        sm, ax=axes[:, 3].ravel().tolist(),
        fraction=0.018, pad=0.015, aspect=30,
    )
    cbar.set_label("mean z (depth)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    fig.suptitle(title, fontsize=12)
    return fig


def _draw_arrow_row(
    ax,
    b: BinnedAxis,
    *,
    depth_cmap,
    z_abs_max: float,
) -> None:
    """
    Per-bin arrow showing the mean (x, y) vector at each bin's projection
    position. Each arrow's tail sits at (bin center on the projection axis,
    0); the head is offset by the scaled mean (x, y); the color encodes the
    mean z component using ``depth_cmap``.

    Arrows share a single linear scale so relative magnitudes across bins are
    comparable. The scale is chosen so the largest in-plane vector takes up
    roughly 80% of the bin spacing, keeping arrows visible without
    overlapping.
    """
    centers = b.centers
    xy = b.xyz_mean[:, :2]
    z = b.xyz_mean[:, 2]
    finite = np.isfinite(b.xyz_mean).all(axis=1)

    ax.set_xlim(centers[0] - 0.5, centers[-1] + 0.5)
    ax.axhline(0, color="lightgrey", lw=0.5, zorder=0)
    ax.set_xlabel("axis projection (z)", fontsize=8)
    ax.set_ylabel("(x, y) component", fontsize=8)

    if not finite.any():
        return

    bin_spacing = float(np.mean(np.diff(centers))) if centers.size >= 2 else 1.0
    in_plane_norms = np.linalg.norm(xy[finite], axis=1)
    max_in_plane = float(in_plane_norms.max()) if in_plane_norms.size else 1.0
    if max_in_plane < 1e-12:
        max_in_plane = 1.0
    arrow_scale = (0.8 * bin_spacing) / max_in_plane

    arrow_max = arrow_scale * max_in_plane
    ax.set_ylim(-1.4 * arrow_max, 1.4 * arrow_max)

    for k in np.where(finite)[0]:
        x0 = float(centers[k])
        dx = arrow_scale * float(xy[k, 0])
        dy = arrow_scale * float(xy[k, 1])
        zc = float(z[k])
        color = depth_cmap(0.5 + 0.5 * (zc / z_abs_max))
        ax.annotate(
            "",
            xy=(x0 + dx, dy),
            xytext=(x0, 0),
            arrowprops=dict(arrowstyle="->", color=color, lw=2.0),
        )
        ax.scatter([x0], [0], color="black", s=8, zorder=3)

    # Faint reference arrow showing how long an in-plane unit looks at this
    # scale, anchored at the upper-left corner of the panel.
    legend_x = centers[0] - 0.4
    legend_y = arrow_max
    ref_len = arrow_scale * max_in_plane
    ax.annotate(
        "",
        xy=(legend_x + ref_len, legend_y),
        xytext=(legend_x, legend_y),
        arrowprops=dict(arrowstyle="->", color="dimgray", lw=1.0),
    )
    ax.text(
        legend_x, legend_y - 0.18 * arrow_max,
        f"|(x,y)| = {max_in_plane:.2f}",
        fontsize=6, color="dimgray",
    )


# ===========================================================================
# Hypothesis-test analysis: position vs shape composition of the preferred
# axis vs the saved orthogonal PCs.
#
# Self-contained class. Reduces every axis to two scalar indices —
# geometric (axis-weight share in the position block) and variance
# partition (R^2 of axis projections regressed on position features) —
# and a signed PSI = 2*R^2_pos - 1 in [-1, +1]. Renders one bar chart per
# JSON; no entanglement with the position-along-axis figure.
# ===========================================================================

class AxisCompositionAnalysis:
    """
    Two complementary indices per axis:

    1. Geometric:  ||a_pos||^2 / ||a||^2.  Fraction of axis squared norm
       in the position block (radialPosition.*, angularPosition.*). Pure
       axis-weight measure; ignores feature correlations.

    2. Variance partition:  R^2_pos = R^2 of axis_proj = X @ a regressed
       on the position features. Direct decomposition: since axis_proj
       lies in span(X), R^2_pos exactly partitions the variance into a
       position-explained share and a non-position-residual share, with
       R^2_nonpos|pos = 1 - R^2_pos.

    PSI = 2 * R^2_pos - 1 maps R^2_pos onto [-1, +1] for a signed read-out:
      +1 = pure position, 0 = balanced, -1 = pure non-position.

    Compares the preferred axis against the top-K saved PCs orthogonal
    to it (already PCA-derived inside the model — see
    compute_all_orthogonal_axes in axis_coding_analysis.py:1001). A
    chance baseline n_pos / n_total is drawn for context: a random unit
    direction's expected geometric / R^2 share.
    """

    POSITION_PREFIXES = ("radialPosition", "angularPosition")

    def __init__(
        self,
        top_k_orth: int = 5,
        position_prefixes: tuple = POSITION_PREFIXES,
    ):
        self.top_k_orth = top_k_orth
        self.position_prefixes = position_prefixes
        self._fitted: Optional[dict] = None

    # ------------------------------------------------------------------ fit

    def fit(
        self,
        X: np.ndarray,
        feature_names: list[str],
        w_in_feature_space: Optional[np.ndarray] = None,
        all_orth_axes_in_feature_space: Optional[np.ndarray] = None,
        all_orth_variances: Optional[np.ndarray] = None,
    ) -> "AxisCompositionAnalysis":
        X = np.asarray(X, dtype=np.float64)
        finite = np.all(np.isfinite(X), axis=1)
        X = X[finite]
        if X.shape[0] < 5:
            self._fitted = {"available": False, "reason": "fewer than 5 valid stims"}
            return self
        if not feature_names or len(feature_names) != X.shape[1]:
            self._fitted = {"available": False, "reason": "feature_names mismatch"}
            return self

        d = X.shape[1]
        pos_mask = np.array([self._is_position(n) for n in feature_names], dtype=bool)
        n_pos = int(pos_mask.sum())
        if n_pos == 0 or n_pos == d:
            self._fitted = {
                "available": False,
                "reason": "no position/non-position partition possible",
            }
            return self
        chance = n_pos / float(d)
        X_pos = X[:, pos_mask]

        # Build the list of axes to score: preferred + top-K orth PCs by var.
        axes_to_score: list[tuple[str, np.ndarray, Optional[float]]] = []

        if w_in_feature_space is not None:
            w = np.asarray(w_in_feature_space, dtype=np.float64)
            if w.size == d and float(np.sum(w * w)) > 1e-12:
                axes_to_score.append(("preferred", w, None))

        if (all_orth_axes_in_feature_space is not None
                and all_orth_variances is not None):
            orth = np.asarray(all_orth_axes_in_feature_space, dtype=np.float64)
            orth_var = np.asarray(all_orth_variances, dtype=np.float64)
            if (orth.ndim == 2 and orth.shape[0] == d
                    and orth.shape[1] == orth_var.size):
                order = np.argsort(-orth_var)
                for rank, k in enumerate(order[: self.top_k_orth]):
                    axis_vec = orth[:, k]
                    if float(np.sum(axis_vec * axis_vec)) < 1e-12:
                        continue
                    axes_to_score.append(
                        (f"PC#{rank + 1} ⊥ w", axis_vec, float(orth_var[k]))
                    )

        if not axes_to_score:
            self._fitted = {"available": False, "reason": "no axes to score"}
            return self

        results = []
        for label, axis, axis_var in axes_to_score:
            axis_norm_sq = float(np.sum(axis * axis))
            geom = float(np.sum(axis[pos_mask] ** 2)) / axis_norm_sq

            axis_proj = X @ axis
            r2_pos = self._r2_on_position(X_pos, axis_proj)
            psi = 2.0 * r2_pos - 1.0

            results.append({
                "label": label,
                "geom_index": float(geom),
                "r2_pos": float(r2_pos),
                "psi": float(psi),
                "axis_var": axis_var,
            })

        self._fitted = {
            "available": True,
            "results": results,
            "chance_baseline": float(chance),
            "n_pos": n_pos,
            "n_total": d,
            "n_used": int(X.shape[0]),
            "position_features": [n for n, m in zip(feature_names, pos_mask) if m],
            "nonpos_features": [n for n, m in zip(feature_names, ~pos_mask) if m],
        }
        return self

    # ---------------------------------------------------------------- helpers

    def _is_position(self, name: str) -> bool:
        return any(name.startswith(p) for p in self.position_prefixes)

    @staticmethod
    def _r2_on_position(X_pos: np.ndarray, axis_proj: np.ndarray) -> float:
        """OLS R^2 of axis_proj regressed on X_pos with intercept."""
        n = X_pos.shape[0]
        proj_c = axis_proj - axis_proj.mean()
        ss_tot = float(np.sum(proj_c * proj_c))
        if ss_tot < 1e-12:
            return 0.0
        design = np.hstack([np.ones((n, 1)), X_pos])
        coefs, *_ = np.linalg.lstsq(design, axis_proj, rcond=None)
        residuals = axis_proj - design @ coefs
        ss_res = float(np.sum(residuals * residuals))
        return float(max(0.0, min(1.0 - ss_res / ss_tot, 1.0)))

    # ---------------------------------------------------------------- render

    def render(self, fig: Optional[plt.Figure] = None) -> plt.Figure:
        """Produce (or fill) a Figure with the axis-composition bar chart."""
        if fig is None:
            fig = plt.figure(figsize=(12, 5), constrained_layout=True)

        fitted = self._fitted
        if fitted is None or not fitted.get("available"):
            ax = fig.add_subplot(1, 1, 1)
            reason = (fitted or {}).get("reason", "not fitted")
            ax.text(
                0.5, 0.5, f"Axis composition: {reason}",
                ha="center", va="center", fontsize=10, color="dimgray",
            )
            ax.axis("off")
            return fig

        results = fitted["results"]
        labels = [r["label"] for r in results]
        geom = np.array([r["geom_index"] for r in results])
        r2pos = np.array([r["r2_pos"] for r in results])
        psi = np.array([r["psi"] for r in results])
        chance = fitted["chance_baseline"]

        ax = fig.add_subplot(1, 1, 1)
        x = np.arange(len(labels))
        width = 0.4
        ax.bar(x - width / 2, geom, width,
               label="‖a_pos‖² / ‖a‖²  (geometric)",
               color="tab:blue", alpha=0.85)
        ax.bar(x + width / 2, r2pos, width,
               label="R²_pos  (variance partition)",
               color="tab:purple", alpha=0.85)
        ax.axhline(
            chance, color="grey", linestyle="--", lw=1.0,
            label=f"chance = {fitted['n_pos']}/{fitted['n_total']} = {chance:.2f}",
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
        ax.set_ylabel("position content")
        ax.set_ylim(0, 1.10)
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.25, axis="y")

        # PSI annotations above each axis group.
        for i, p in enumerate(psi):
            top = max(geom[i], r2pos[i])
            ax.annotate(
                f"PSI={p:+.2f}",
                xy=(i, top + 0.025),
                ha="center", va="bottom",
                fontsize=8, color="black",
            )

        if results:
            r0 = results[0]
            ax.set_title(
                f"Axis composition  |  preferred: geom={r0['geom_index']:.2f}, "
                f"R²_pos={r0['r2_pos']:.2f}, PSI={r0['psi']:+.2f}  |  "
                f"n_stim={fitted['n_used']}",
                fontsize=11,
            )
        return fig


# ---------------------------------------------------------------------------
# Per-JSON driver
# ---------------------------------------------------------------------------

def process_json(
    json_path: str,
    components_by_stim_factory,  # callable: component_type -> {stim_id: comps}
    *,
    top_orth: int,
    n_bins: int,
    z_range: float,
    top_k_composition: int = 5,
) -> Optional[str]:
    """Render and save one figure for ``json_path``. Returns the saved path."""
    with open(json_path, "r") as f:
        result = json.load(f)

    component_type = result.get("component_type")
    channel = result.get("channel")
    strategy_label = result.get("strategy_label")
    stim_ids = result.get("stim_ids") or []
    selected_indices = result.get("selected_indices") or []
    axis_projections = result.get("axis_projections")
    all_orth_proj = result.get("all_orthogonal_projections")
    all_orth_var = result.get("all_orthogonal_variances")
    mu_decoded = result.get("mu_decoded")

    if not stim_ids or axis_projections is None:
        print(f"  [skip] {os.path.basename(json_path)}: missing stim_ids or projections.")
        return None
    if len(selected_indices) != len(stim_ids):
        print(
            f"  [skip] {os.path.basename(json_path)}: selected_indices/stim_ids "
            f"length mismatch ({len(selected_indices)} vs {len(stim_ids)})."
        )
        return None

    components_by_stim = components_by_stim_factory(component_type)

    pos = _extract_positions(stim_ids, selected_indices, components_by_stim)
    if not pos.valid_mask.any():
        print(
            f"  [skip] {os.path.basename(json_path)}: no stim with extractable "
            f"position for component_type={component_type}."
        )
        return None

    rows: list[BinnedAxis] = [
        _bin_axis(
            np.asarray(axis_projections, dtype=np.float64),
            pos,
            label="preferred",
            n_bins=n_bins,
            z_range=z_range,
        )
    ]

    if all_orth_proj is not None and all_orth_var is not None:
        all_orth_proj = np.asarray(all_orth_proj, dtype=np.float64)  # (n_stim, n_orth)
        all_orth_var = np.asarray(all_orth_var, dtype=np.float64)
        if all_orth_proj.ndim == 2 and all_orth_proj.shape[1] >= 1:
            order = np.argsort(-all_orth_var)
            for rank, k in enumerate(order[:top_orth]):
                rows.append(
                    _bin_axis(
                        all_orth_proj[:, k],
                        pos,
                        label=f"PC#{rank + 1} ⊥ w",
                        n_bins=n_bins,
                        z_range=z_range,
                        axis_variance=float(all_orth_var[k]),
                    )
                )

    # ------------------------------------------------------------------
    # Figure 1: position-along-axis (descriptive).
    # ------------------------------------------------------------------
    title = (
        f"Position along axis  |  channel={channel}  "
        f"type={component_type}  strategy={strategy_label}"
    )
    fig = _plot_figure(rows, title, mu_decoded)
    out_path = os.path.join(
        os.path.dirname(json_path),
        f"position_along_axis_{channel}_{component_type}_{strategy_label}.png",
    )
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {out_path}")

    # ------------------------------------------------------------------
    # Figure 2: axis composition (hypothesis test). Self-contained class —
    # owns its own design-matrix consumption, indices, and rendering.
    # Skips silently if the design matrix can't be rebuilt or the JSON
    # lacks feature-space axes.
    # ------------------------------------------------------------------
    try:
        X, feature_names = _build_design_matrix_for_json(
            stim_ids, selected_indices, components_by_stim, component_type,
        )
        composition = AxisCompositionAnalysis(top_k_orth=top_k_composition).fit(
            X=X,
            feature_names=feature_names,
            w_in_feature_space=result.get("w_in_feature_space"),
            all_orth_axes_in_feature_space=result.get(
                "all_orthogonal_axes_in_feature_space"
            ),
            all_orth_variances=result.get("all_orthogonal_variances"),
        )
        comp_fig = composition.render()
        comp_fig.suptitle(
            f"channel={channel}  type={component_type}  "
            f"strategy={strategy_label}",
            fontsize=10,
        )
        comp_out = os.path.join(
            os.path.dirname(json_path),
            f"axis_composition_{channel}_{component_type}_{strategy_label}.png",
        )
        comp_fig.savefig(comp_out, dpi=150, bbox_inches="tight")
        plt.close(comp_fig)
        print(f"  saved: {comp_out}")
    except Exception as exc:
        print(f"  [composition] skipped ({exc})")
        import traceback
        traceback.print_exc()
    return out_path


# ---------------------------------------------------------------------------
# Entry point — edit the variables below and run this file directly.
# ---------------------------------------------------------------------------

def main():
    # Directory containing the axis_coding_*.json model files.
    save_dir = "/home/connorlab/Documents/plots/<session_id>/axis_coding"

    # Session id used to fetch the source df (post-conditioning).
    session_id = "260426_0"

    # How many orthogonal axes (top by variance from the saved 300) to plot
    # alongside the preferred axis.
    top_orth = 3

    # Binning for the per-axis tuning curves.
    n_bins = 9
    z_range = 2.0

    # Number of top orthogonal PCs (already PCA-derived inside the model)
    # to score alongside the preferred axis in the composition figure.
    top_k_composition = 5

    # ----------------------------------------------------------------------

    save_dir = os.path.abspath(save_dir)
    if not os.path.isdir(save_dir):
        raise FileNotFoundError(f"save_dir not found: {save_dir}")

    json_paths = sorted(glob.glob(os.path.join(save_dir, "axis_coding_*.json")))
    if not json_paths:
        raise FileNotFoundError(f"No axis_coding_*.json in {save_dir}")

    print(f"[position_along_axis] {len(json_paths)} JSONs in {save_dir}")
    df = _prepare_session_df(session_id)

    cache: dict[str, dict] = {}

    def factory(component_type: str) -> dict:
        if component_type not in cache:
            cache[component_type] = _per_stim_components(df, component_type)
            print(
                f"  [df] {component_type}: "
                f"{len(cache[component_type])} stim with components."
            )
        return cache[component_type]

    n_ok = 0
    for path in json_paths:
        print(f"\n[{os.path.basename(path)}]")
        try:
            if process_json(
                path, factory,
                top_orth=top_orth,
                n_bins=n_bins,
                z_range=z_range,
                top_k_composition=top_k_composition,
            ) is not None:
                n_ok += 1
        except Exception as exc:
            print(f"  [error] {exc}")
            import traceback
            traceback.print_exc()

    print(f"\n[position_along_axis] done — {n_ok}/{len(json_paths)} figures written.")


if __name__ == "__main__":
    main()

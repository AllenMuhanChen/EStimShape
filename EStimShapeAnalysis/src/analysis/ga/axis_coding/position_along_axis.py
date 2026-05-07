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
        if comps_enc is None:
            for cast in (int, str, float):
                try:
                    alt = cast(sid)
                except (TypeError, ValueError):
                    continue
                if alt == sid:
                    continue
                comps_enc = encoded.get(alt)
                if comps_enc is not None:
                    break
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

    n_no_comps = 0
    n_idx_oor = 0
    n_field_miss = 0
    for i, sid in enumerate(stim_ids):
        comps = components_by_stim.get(sid)
        # Fall back through alternate type representations of the stim id —
        # JSON-parsed ints vs str(StimSpecId) in the df both happen.
        if not comps:
            for cast in (int, str, float):
                try:
                    alt = cast(sid)
                except (TypeError, ValueError):
                    continue
                if alt == sid:
                    continue
                comps = components_by_stim.get(alt)
                if comps:
                    break
        if not comps:
            n_no_comps += 1
            continue

        idx = int(selected_indices[i])
        if idx < 0 or idx >= len(comps):
            n_idx_oor += 1
            continue

        comp = comps[idx]
        try:
            r = float(comp["radialPosition"])
            t = float(comp["angularPosition"]["theta"])
            p = float(comp["angularPosition"]["phi"])
        except (KeyError, TypeError, ValueError):
            n_field_miss += 1
            continue

        radial[i] = r
        theta[i] = t
        phi[i] = p
        sin_phi = np.sin(p)
        xyz[i] = r * np.array(
            [sin_phi * np.cos(t), sin_phi * np.sin(t), np.cos(p)]
        )
        valid[i] = True

    n_warn = n_no_comps + n_idx_oor + n_field_miss
    if n_warn:
        print(
            f"  [position] warning: {n_warn}/{n} stim dropped — "
            f"no_comps={n_no_comps}, idx_OOR={n_idx_oor}, "
            f"field_missing={n_field_miss}"
        )
        # When the dominant failure mode is "no_comps", almost always a
        # stim_id type / membership mismatch. Print samples so the next
        # rerun makes the cause obvious.
        if n_no_comps and n_no_comps == n_warn:
            df_keys = list(components_by_stim.keys())[:3]
            json_sids = list(stim_ids[:3])
            print(
                f"    df components_by_stim: n_keys={len(components_by_stim)}, "
                f"sample={df_keys} "
                f"(types: {[type(k).__name__ for k in df_keys]})"
            )
            print(
                f"    json stim_ids:         n={len(stim_ids)}, "
                f"sample={json_sids} "
                f"(types: {[type(s).__name__ for s in json_sids]})"
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
    Per-axis position-vs-shape decomposition. For each axis a, regress the
    per-stim axis projection axis_proj = X @ a on each feature block
    separately and report the two block-only R²s:

      - R²_pos    : R² of axis_proj regressed on position features alone.
      - R²_shape  : R² of axis_proj regressed on non-position (shape)
                    features alone.

    These are NOT a partition. With correlated feature blocks they can sum
    to more than 1 (overlap) or less (when neither block alone explains
    the axis well). That's by design: the gap between them is the
    informative bit.

    PSI = R²_pos − R²_shape in [-1, +1] is a signed position-vs-shape
    index — positive means position dominates, negative means shape
    dominates, near zero means both blocks alone explain the axis equally.

    Compares the preferred axis against the top-K saved PCs orthogonal
    to it (already PCA-derived inside the model — see
    compute_all_orthogonal_axes in axis_coding_analysis.py:1001). A
    chance baseline n_pos / n_total is drawn for context.
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
        X_shape = X[:, ~pos_mask]

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
            axis_proj = X @ axis
            r2_pos = self._r2_on_block(X_pos, axis_proj)
            r2_shape = self._r2_on_block(X_shape, axis_proj)
            psi = r2_pos - r2_shape

            results.append({
                "label": label,
                "r2_pos": float(r2_pos),
                "r2_shape": float(r2_shape),
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
    def _r2_on_block(X_block: np.ndarray, axis_proj: np.ndarray) -> float:
        """OLS R^2 of axis_proj regressed on X_block with intercept."""
        if X_block.shape[1] == 0:
            return 0.0
        n = X_block.shape[0]
        proj_c = axis_proj - axis_proj.mean()
        ss_tot = float(np.sum(proj_c * proj_c))
        if ss_tot < 1e-12:
            return 0.0
        design = np.hstack([np.ones((n, 1)), X_block])
        coefs, *_ = np.linalg.lstsq(design, axis_proj, rcond=None)
        residuals = axis_proj - design @ coefs
        ss_res = float(np.sum(residuals * residuals))
        return float(max(0.0, min(1.0 - ss_res / ss_tot, 1.0)))

    # ---------------------------------------------------------------- export

    def to_db_rows(self) -> list[dict]:
        """
        Per-axis rows for export to AxisCompositionMetrics. Empty when
        not fitted or unavailable. ``axis_rank`` is 0 for the preferred
        axis and 1, 2, ... for the orthogonal PCs in saved-variance order.
        """
        fitted = self._fitted
        if not fitted or not fitted.get("available"):
            return []
        rows = []
        for rank, r in enumerate(fitted["results"]):
            rows.append({
                "axis_label": r["label"],
                "axis_rank": int(rank),
                "r2_pos": float(r["r2_pos"]),
                "r2_shape": float(r["r2_shape"]),
                "psi": float(r["psi"]),
                "axis_variance": (
                    None if r.get("axis_var") is None else float(r["axis_var"])
                ),
                "chance_baseline_pos": float(fitted["chance_baseline"]),
                "n_stim_used": int(fitted["n_used"]),
            })
        return rows

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
        r2pos = np.array([r["r2_pos"] for r in results])
        r2shape = np.array([r["r2_shape"] for r in results])
        psi = np.array([r["psi"] for r in results])
        chance = fitted["chance_baseline"]
        chance_shape = 1.0 - chance

        ax = fig.add_subplot(1, 1, 1)
        x = np.arange(len(labels))
        width = 0.4
        ax.bar(x - width / 2, r2pos, width,
               label="R²_pos   (axis_proj ~ position features)",
               color="tab:blue", alpha=0.85)
        ax.bar(x + width / 2, r2shape, width,
               label="R²_shape (axis_proj ~ non-position features)",
               color="tab:orange", alpha=0.85)
        ax.axhline(
            chance, color="tab:blue", linestyle=":", lw=1.0, alpha=0.7,
            label=f"chance R²_pos   = {fitted['n_pos']}/{fitted['n_total']} = {chance:.2f}",
        )
        ax.axhline(
            chance_shape, color="tab:orange", linestyle=":", lw=1.0, alpha=0.7,
            label=f"chance R²_shape = {fitted['n_total'] - fitted['n_pos']}/{fitted['n_total']} = {chance_shape:.2f}",
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
        ax.set_ylabel("variance of axis projection explained (R²)")
        ax.set_ylim(0, 1.15)
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.25, axis="y")

        # PSI annotations above each axis group.
        for i, p in enumerate(psi):
            top = max(r2pos[i], r2shape[i])
            ax.annotate(
                f"PSI={p:+.2f}",
                xy=(i, top + 0.03),
                ha="center", va="bottom",
                fontsize=8, color="black",
            )

        if results:
            r0 = results[0]
            ax.set_title(
                f"Axis composition  |  preferred: R²_pos={r0['r2_pos']:.2f}, "
                f"R²_shape={r0['r2_shape']:.2f}, PSI={r0['psi']:+.2f}  |  "
                f"n_stim={fitted['n_used']}",
                fontsize=11,
            )
        return fig


# ===========================================================================
# Hypothesis-test analysis: are the position and shape axes independent?
#
# Self-contained class. Owns its own ridge fits for "best position-only"
# and "best shape-only" axes, the additive-vs-interaction CV R² test, and
# the per-bin shape-tuning overlay. Uses the cell's actual responses
# (not axis projections) as the dependent variable — the goal is to ask
# how the response factorizes, not to characterize the saved preferred
# axis.
# ===========================================================================

class AxisIndependenceAnalysis:
    """
    Decompose the response into position-driven and shape-driven parts and
    ask whether the two combine additively (independent axes) or
    interactively (intertwined axes).

    Pipeline:
      1. Partition feature_names into position vs non-position blocks.
      2. RidgeCV: y ~ X_pos -> w_p (in position subspace). p_proj = X_pos @ w_p.
      3. RidgeCV: y ~ X_shape -> w_s. s_proj = X_shape @ w_s.
      4. Cross-validated R² for four nested models with [p_proj, s_proj]
         as features:
           pos_only:    y ~ p_proj
           shape_only:  y ~ s_proj
           additive:    y ~ p_proj + s_proj
           interaction: y ~ p_proj + s_proj + p_proj * s_proj
         The interaction-minus-additive gap is the headline scalar.
      5. Bin stims by p_proj into n_position_bins (parameterized — 3 is
         often too coarse; 5–7 is a good default). Within each bin compute
         the shape tuning curve (response vs s_proj_perp, where s_proj_perp
         is s_proj residualized against p_proj across all stims so the
         within-bin range isn't restricted by the cross-axis correlation).
         Overlapping curves -> independent. Differently shaped curves ->
         intertwined.

    Renders three panels in one Figure:
      A. (p_proj, s_proj) heatmap of mean response, with 1D marginals on
         top + right; an inset shows the (p_proj, s_proj) scatter to make
         the cross-axis correlation visible.
      B. Bar chart of CV R² for the four nested models.
      C. Per-bin shape tuning curves (response vs s_proj_perp), one curve
         per p_proj bin, color-coded by bin position.
    """

    POSITION_PREFIXES = ("radialPosition", "angularPosition")

    def __init__(
        self,
        n_position_bins: int = 5,
        n_shape_bins: int = 9,
        n_heatmap_bins: int = 8,
        ridge_alphas: tuple = (0.01, 0.1, 1.0, 10.0, 100.0),
        cv_n_folds: int = 5,
        position_prefixes: tuple = POSITION_PREFIXES,
    ):
        self.n_position_bins = int(n_position_bins)
        self.n_shape_bins = int(n_shape_bins)
        self.n_heatmap_bins = int(n_heatmap_bins)
        self.ridge_alphas = tuple(ridge_alphas)
        self.cv_n_folds = int(cv_n_folds)
        self.position_prefixes = position_prefixes
        self._fitted: Optional[dict] = None

    # ------------------------------------------------------------------ fit

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
    ) -> "AxisIndependenceAnalysis":
        from sklearn.linear_model import RidgeCV
        from sklearn.model_selection import KFold, cross_val_score

        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).ravel()
        finite = np.all(np.isfinite(X), axis=1) & np.isfinite(y)
        X = X[finite]
        y = y[finite]
        if X.shape[0] < max(20, 2 * self.cv_n_folds):
            self._fitted = {"available": False, "reason": "too few stims for CV"}
            return self
        if not feature_names or len(feature_names) != X.shape[1]:
            self._fitted = {"available": False, "reason": "feature_names mismatch"}
            return self

        d = X.shape[1]
        pos_mask = np.array([self._is_position(n) for n in feature_names], dtype=bool)
        if pos_mask.sum() == 0 or pos_mask.sum() == d:
            self._fitted = {"available": False, "reason": "no position/shape partition"}
            return self

        X_pos = X[:, pos_mask]
        X_shape = X[:, ~pos_mask]

        # Best position-only and shape-only axes (RidgeCV).
        ridge_p = RidgeCV(alphas=self.ridge_alphas).fit(X_pos, y)
        ridge_s = RidgeCV(alphas=self.ridge_alphas).fit(X_shape, y)
        # Pure subspace projections (no intercept; centering handled below).
        p_proj = X_pos @ ridge_p.coef_
        s_proj = X_shape @ ridge_s.coef_

        # Standardize projections so coefficients are on comparable scales
        # in the additive and interaction regressions.
        p_z = self._zscore(p_proj)
        s_z = self._zscore(s_proj)

        kf = KFold(n_splits=self.cv_n_folds, shuffle=True, random_state=0)

        def cv_r2(features: np.ndarray) -> float:
            scores = cross_val_score(
                RidgeCV(alphas=self.ridge_alphas),
                features, y, cv=kf, scoring="r2",
            )
            return float(np.mean(scores))

        feats_p = p_z.reshape(-1, 1)
        feats_s = s_z.reshape(-1, 1)
        feats_add = np.column_stack([p_z, s_z])
        feats_int = np.column_stack([p_z, s_z, p_z * s_z])

        r2_p = cv_r2(feats_p)
        r2_s = cv_r2(feats_s)
        r2_add = cv_r2(feats_add)
        r2_int = cv_r2(feats_int)
        interaction_gap = r2_int - r2_add

        # Pearson correlation between the two projections across stims.
        corr_ps = float(np.corrcoef(p_z, s_z)[0, 1])

        # Residualize shape projection against position projection so the
        # within-bin range of s_proj isn't artificially restricted by the
        # (p_z, s_z) correlation. Used by Panel C.
        beta = float(np.dot(p_z, s_z) / max(np.dot(p_z, p_z), 1e-12))
        s_perp = s_z - beta * p_z

        # Heatmap: mean response on a (p_z, s_z) grid.
        heatmap = self._mean_response_grid(
            p_z, s_z, y, n_bins=self.n_heatmap_bins,
        )

        # Per-position-bin shape tuning curves (response vs s_perp).
        per_bin_curves = self._per_position_bin_tuning(
            p_z, s_perp, y,
            n_position_bins=self.n_position_bins,
            n_shape_bins=self.n_shape_bins,
        )

        # 1D marginals of the heatmap (averaged response in each axis bin).
        marginals = self._marginals(p_z, s_z, y, n_bins=self.n_heatmap_bins)

        self._fitted = {
            "available": True,
            "n_used": int(X.shape[0]),
            "r2_p": r2_p,
            "r2_s": r2_s,
            "r2_add": r2_add,
            "r2_int": r2_int,
            "interaction_gap": float(interaction_gap),
            "corr_ps": corr_ps,
            "p_z": p_z,
            "s_z": s_z,
            "y": y,
            "heatmap": heatmap,
            "marginals": marginals,
            "per_bin_curves": per_bin_curves,
            "n_position_bins": self.n_position_bins,
            "ridge_alpha_p": float(ridge_p.alpha_),
            "ridge_alpha_s": float(ridge_s.alpha_),
        }
        return self

    # ---------------------------------------------------------------- helpers

    def _is_position(self, name: str) -> bool:
        return any(name.startswith(p) for p in self.position_prefixes)

    @staticmethod
    def _zscore(v: np.ndarray) -> np.ndarray:
        v = np.asarray(v, dtype=np.float64).ravel()
        m = float(v.mean())
        s = float(v.std(ddof=1)) if v.size >= 2 else 1.0
        if s < 1e-12:
            s = 1.0
        return (v - m) / s

    @staticmethod
    def _bin_edges(z: np.ndarray, n_bins: int) -> np.ndarray:
        # Symmetric edges in z-units; clip to data range.
        lo = float(np.nanpercentile(z, 1))
        hi = float(np.nanpercentile(z, 99))
        lo = min(lo, -2.0)
        hi = max(hi, 2.0)
        return np.linspace(lo, hi, n_bins + 1)

    def _mean_response_grid(self, p_z, s_z, y, *, n_bins: int) -> dict:
        p_edges = self._bin_edges(p_z, n_bins)
        s_edges = self._bin_edges(s_z, n_bins)
        p_idx = np.clip(np.digitize(p_z, p_edges) - 1, 0, n_bins - 1)
        s_idx = np.clip(np.digitize(s_z, s_edges) - 1, 0, n_bins - 1)
        grid_mean = np.full((n_bins, n_bins), np.nan)
        grid_n = np.zeros((n_bins, n_bins), dtype=int)
        for ip in range(n_bins):
            for is_ in range(n_bins):
                sel = (p_idx == ip) & (s_idx == is_)
                n = int(sel.sum())
                grid_n[ip, is_] = n
                if n > 0:
                    grid_mean[ip, is_] = float(y[sel].mean())
        return {
            "mean": grid_mean,           # (n_bins, n_bins) indexed [p, s]
            "count": grid_n,
            "p_edges": p_edges,
            "s_edges": s_edges,
        }

    def _marginals(self, p_z, s_z, y, *, n_bins: int) -> dict:
        p_edges = self._bin_edges(p_z, n_bins)
        s_edges = self._bin_edges(s_z, n_bins)
        p_centers = 0.5 * (p_edges[:-1] + p_edges[1:])
        s_centers = 0.5 * (s_edges[:-1] + s_edges[1:])
        p_idx = np.clip(np.digitize(p_z, p_edges) - 1, 0, n_bins - 1)
        s_idx = np.clip(np.digitize(s_z, s_edges) - 1, 0, n_bins - 1)

        def avg(idx):
            m = np.full(n_bins, np.nan)
            sem = np.full(n_bins, np.nan)
            for b in range(n_bins):
                sel = idx == b
                n = int(sel.sum())
                if n == 0:
                    continue
                vals = y[sel]
                m[b] = float(vals.mean())
                sem[b] = float(vals.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
            return m, sem

        p_mean, p_sem = avg(p_idx)
        s_mean, s_sem = avg(s_idx)
        return {
            "p_centers": p_centers, "p_mean": p_mean, "p_sem": p_sem,
            "s_centers": s_centers, "s_mean": s_mean, "s_sem": s_sem,
        }

    def _per_position_bin_tuning(
        self, p_z, s_perp, y, *, n_position_bins: int, n_shape_bins: int,
    ) -> list[dict]:
        # Equal-count quantile bins along p_z so each bin holds a similar
        # number of stims.
        quantiles = np.linspace(0, 1, n_position_bins + 1)
        p_edges = np.quantile(p_z, quantiles)
        # Disambiguate ties by nudging right-edges very slightly.
        for i in range(1, len(p_edges)):
            if p_edges[i] <= p_edges[i - 1]:
                p_edges[i] = p_edges[i - 1] + 1e-12
        p_idx = np.clip(np.digitize(p_z, p_edges) - 1, 0, n_position_bins - 1)

        s_edges = self._bin_edges(s_perp, n_shape_bins)
        s_centers = 0.5 * (s_edges[:-1] + s_edges[1:])

        curves = []
        for b in range(n_position_bins):
            in_bin = p_idx == b
            n_in_bin = int(in_bin.sum())
            mean = np.full(n_shape_bins, np.nan)
            sem = np.full(n_shape_bins, np.nan)
            counts = np.zeros(n_shape_bins, dtype=int)
            if n_in_bin > 0:
                s_idx = np.clip(np.digitize(s_perp[in_bin], s_edges) - 1, 0, n_shape_bins - 1)
                y_in_bin = y[in_bin]
                for sb in range(n_shape_bins):
                    sel = s_idx == sb
                    n = int(sel.sum())
                    counts[sb] = n
                    if n > 0:
                        vals = y_in_bin[sel]
                        mean[sb] = float(vals.mean())
                        sem[sb] = float(vals.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
            p_lo, p_hi = float(p_edges[b]), float(p_edges[b + 1])
            curves.append({
                "p_lo": p_lo, "p_hi": p_hi,
                "n_in_bin": n_in_bin,
                "centers": s_centers,
                "mean": mean,
                "sem": sem,
                "counts": counts,
            })
        return curves

    # ---------------------------------------------------------------- export

    def to_db_row(self) -> Optional[dict]:
        """Scalars for export to AxisIndependenceMetrics. None if not fitted."""
        fitted = self._fitted
        if not fitted or not fitted.get("available"):
            return None
        return {
            "n_stim_used": int(fitted["n_used"]),
            "r2_pos_only": float(fitted["r2_p"]),
            "r2_shape_only": float(fitted["r2_s"]),
            "r2_additive": float(fitted["r2_add"]),
            "r2_interaction": float(fitted["r2_int"]),
            "interaction_gap": float(fitted["interaction_gap"]),
            "corr_p_s": float(fitted["corr_ps"]),
            "ridge_alpha_p": float(fitted["ridge_alpha_p"]),
            "ridge_alpha_s": float(fitted["ridge_alpha_s"]),
        }

    # ---------------------------------------------------------------- render

    def render(self, fig: Optional[plt.Figure] = None) -> plt.Figure:
        if fig is None:
            fig = plt.figure(figsize=(16, 10), constrained_layout=True)

        fitted = self._fitted
        if fitted is None or not fitted.get("available"):
            ax = fig.add_subplot(1, 1, 1)
            reason = (fitted or {}).get("reason", "not fitted")
            ax.text(
                0.5, 0.5, f"Axis independence: {reason}",
                ha="center", va="center", fontsize=10, color="dimgray",
            )
            ax.axis("off")
            return fig

        gs = fig.add_gridspec(
            nrows=2, ncols=2,
            height_ratios=[1.0, 0.9],
            width_ratios=[1.6, 1.0],
        )
        self._draw_panel_a_heatmap(fig, gs[0, 0], fitted)
        self._draw_panel_b_bars(fig, gs[0, 1], fitted)
        self._draw_panel_c_curves(fig, gs[1, :], fitted)

        fig.suptitle(
            f"Axis independence  |  R²_add={fitted['r2_add']:.2f}  "
            f"R²_int={fitted['r2_int']:.2f}  "
            f"interaction gap={fitted['interaction_gap']:+.3f}  |  "
            f"corr(p_proj, s_proj)={fitted['corr_ps']:+.2f}  |  "
            f"n_stim={fitted['n_used']}",
            fontsize=11,
        )
        return fig

    def _draw_panel_a_heatmap(self, fig, gs_cell, fitted):
        # Heatmap with marginals using a sub-gridspec inside the cell.
        sub = gs_cell.subgridspec(
            nrows=2, ncols=2,
            height_ratios=[0.25, 1.0],
            width_ratios=[1.0, 0.25],
            hspace=0.05, wspace=0.05,
        )
        ax_top = fig.add_subplot(sub[0, 0])
        ax_main = fig.add_subplot(sub[1, 0], sharex=ax_top)
        ax_right = fig.add_subplot(sub[1, 1], sharey=ax_main)

        hm = fitted["heatmap"]
        marg = fitted["marginals"]

        # imshow expects rows = y axis. We'll display with s_z on Y, p_z on X,
        # so transpose grid_mean from [p, s] to [s, p].
        im = ax_main.imshow(
            hm["mean"].T,
            origin="lower",
            extent=(hm["p_edges"][0], hm["p_edges"][-1],
                    hm["s_edges"][0], hm["s_edges"][-1]),
            aspect="auto",
            cmap="viridis",
            interpolation="nearest",
        )
        ax_main.set_xlabel("position projection (z)", fontsize=9)
        ax_main.set_ylabel("shape projection (z)", fontsize=9)
        cbar = fig.colorbar(im, ax=ax_main, fraction=0.04, pad=0.02)
        cbar.set_label("mean response", fontsize=8)
        cbar.ax.tick_params(labelsize=7)

        # Top marginal: response vs p_proj.
        ax_top.errorbar(
            marg["p_centers"], marg["p_mean"], yerr=marg["p_sem"],
            fmt="o-", color="tab:blue", capsize=2, lw=1.0, ms=3,
        )
        ax_top.set_ylabel("ŷ | p", fontsize=8)
        ax_top.tick_params(axis="x", labelbottom=False, labelsize=7)
        ax_top.tick_params(axis="y", labelsize=7)
        ax_top.grid(alpha=0.25)

        # Right marginal: response vs s_proj (rotated).
        ax_right.errorbar(
            marg["s_mean"], marg["s_centers"], xerr=marg["s_sem"],
            fmt="o-", color="tab:orange", capsize=2, lw=1.0, ms=3,
        )
        ax_right.set_xlabel("ŷ | s", fontsize=8)
        ax_right.tick_params(axis="y", labelleft=False, labelsize=7)
        ax_right.tick_params(axis="x", labelsize=7)
        ax_right.grid(alpha=0.25)

        # Inset: scatter of (p_z, s_z) so the cross-axis correlation is
        # visible — restricted within-bin range is the confound that
        # motivates s_perp in Panel C.
        inset = ax_main.inset_axes([0.03, 0.74, 0.30, 0.24])
        inset.scatter(
            fitted["p_z"], fitted["s_z"],
            s=4, alpha=0.35, color="white", edgecolors="black", linewidths=0.2,
        )
        inset.set_xticks([]); inset.set_yticks([])
        inset.set_title(
            f"corr(p,s)={fitted['corr_ps']:+.2f}",
            fontsize=7, color="white",
        )
        inset.set_facecolor("#222222")
        for spine in inset.spines.values():
            spine.set_edgecolor("white")
        ax_main.tick_params(labelsize=7)

    def _draw_panel_b_bars(self, fig, gs_cell, fitted):
        ax = fig.add_subplot(gs_cell)
        labels = ["pos only", "shape only", "additive", "interaction"]
        values = np.array([
            fitted["r2_p"], fitted["r2_s"], fitted["r2_add"], fitted["r2_int"],
        ])
        colors = ["tab:blue", "tab:orange", "tab:gray", "tab:purple"]
        x = np.arange(len(labels))
        bars = ax.bar(x, values, color=colors, alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=15, ha="right", fontsize=8)
        ax.set_ylabel("CV R²", fontsize=9)
        ax.set_title(
            f"interaction − additive = {fitted['interaction_gap']:+.3f}",
            fontsize=9,
        )
        ax.axhline(0, color="lightgrey", lw=0.5)
        ax.grid(alpha=0.25, axis="y")
        ax.tick_params(labelsize=7)
        for b, v in zip(bars, values):
            ax.annotate(
                f"{v:+.3f}",
                xy=(b.get_x() + b.get_width() / 2, v),
                xytext=(0, 3 if v >= 0 else -10),
                textcoords="offset points",
                ha="center", fontsize=7,
            )

    def _draw_panel_c_curves(self, fig, gs_cell, fitted):
        ax = fig.add_subplot(gs_cell)
        curves = fitted["per_bin_curves"]
        n_bins = len(curves)
        cmap = plt.get_cmap("viridis")

        for i, c in enumerate(curves):
            color = cmap(i / max(n_bins - 1, 1))
            label = (
                f"p ∈ [{c['p_lo']:+.2f}, {c['p_hi']:+.2f}]   "
                f"n={c['n_in_bin']}"
            )
            ax.errorbar(
                c["centers"], c["mean"], yerr=c["sem"],
                fmt="o-", color=color, capsize=2, lw=1.2, ms=4,
                label=label,
            )

        ax.set_xlabel("shape projection ⟂ position  (s_perp, z)", fontsize=9)
        ax.set_ylabel("mean response", fontsize=9)
        ax.set_title(
            f"Shape tuning per position-projection quantile bin "
            f"(n_position_bins={n_bins}).  "
            "Overlapping curves ⇒ axes independent; differently shaped ⇒ intertwined.",
            fontsize=10,
        )
        ax.legend(fontsize=7, loc="best")
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=8)


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
    n_position_bins: int = 5,
    session_id: Optional[str] = None,
    unit_name: Optional[str] = None,
    repo_conn=None,
) -> Optional[str]:
    """
    Render figures for one ``json_path`` and optionally upsert composition +
    independence metrics into the data repository.

    DB writes happen only when ``session_id``, ``unit_name``, and
    ``repo_conn`` are all provided. Failures during DB write are caught
    and logged so a transient repo issue can't take down the figure
    pipeline.
    """
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

        if repo_conn is not None and session_id and unit_name:
            try:
                from src.repository.export_axis_independence import (
                    export_axis_composition_metrics,
                )
                axis_rows = composition.to_db_rows()
                if axis_rows:
                    export_axis_composition_metrics(
                        repo_conn=repo_conn,
                        session_id=session_id,
                        unit_name=unit_name,
                        component_type=component_type,
                        strategy=strategy_label,
                        axis_rows=axis_rows,
                    )
                    print(
                        f"  [db] AxisCompositionMetrics: "
                        f"{len(axis_rows)} axes upserted"
                    )
            except Exception as exc:
                print(f"  [db composition] failed: {exc}")
    except Exception as exc:
        print(f"  [composition] skipped ({exc})")
        import traceback
        traceback.print_exc()

    # ------------------------------------------------------------------
    # Figure 3: axis independence (additive vs interaction, with the
    # per-position-bin shape tuning overlay). Self-contained class —
    # owns its own ridge fits, CV scoring, and rendering.
    # ------------------------------------------------------------------
    actual_responses = result.get("actual_responses")
    if actual_responses is None:
        print("  [independence] skipped (no actual_responses in JSON)")
    else:
        try:
            X_ind, feature_names_ind = _build_design_matrix_for_json(
                stim_ids, selected_indices, components_by_stim, component_type,
            )
            independence = AxisIndependenceAnalysis(
                n_position_bins=n_position_bins,
            ).fit(
                X=X_ind,
                y=np.asarray(actual_responses, dtype=np.float64),
                feature_names=feature_names_ind,
            )
            ind_fig = independence.render()
            ind_fig.text(
                0.01, 0.985,
                f"channel={channel}  type={component_type}  "
                f"strategy={strategy_label}",
                fontsize=9, color="dimgray", ha="left", va="top",
            )
            ind_out = os.path.join(
                os.path.dirname(json_path),
                f"axis_independence_{channel}_{component_type}_{strategy_label}.png",
            )
            ind_fig.savefig(ind_out, dpi=150, bbox_inches="tight")
            plt.close(ind_fig)
            print(f"  saved: {ind_out}")

            if repo_conn is not None and session_id and unit_name:
                try:
                    from src.repository.export_axis_independence import (
                        export_axis_independence_metrics,
                    )
                    scalars = independence.to_db_row()
                    if scalars is not None:
                        export_axis_independence_metrics(
                            repo_conn=repo_conn,
                            session_id=session_id,
                            unit_name=unit_name,
                            component_type=component_type,
                            strategy=strategy_label,
                            scalars=scalars,
                        )
                        print("  [db] AxisIndependenceMetrics: 1 row upserted")
                except Exception as exc:
                    print(f"  [db independence] failed: {exc}")
        except Exception as exc:
            print(f"  [independence] skipped ({exc})")
            import traceback
            traceback.print_exc()

    return out_path


# ---------------------------------------------------------------------------
# Entry point — edit the variables below and run this file directly.
# ---------------------------------------------------------------------------

def main():

    # Session id used to fetch the source df (post-conditioning).
    session_id = "260423_0"

    # Directory containing the axis_coding_*.json model files.
    save_dir = f"/home/connorlab/Documents/plots/{session_id}/axis_coding"



    # How many orthogonal axes (top by variance from the saved 300) to plot
    # alongside the preferred axis.
    top_orth = 3

    # Binning for the per-axis tuning curves.
    n_bins = 9
    z_range = 2.0

    # Number of top orthogonal PCs (already PCA-derived inside the model)
    # to score alongside the preferred axis in the composition figure.
    top_k_composition = 5

    # Number of position-projection quantile bins for the per-bin shape
    # tuning overlay in the axis-independence figure (Panel C). 3 is
    # often too coarse to see structure; 5–7 is a usable default.
    n_position_bins = 5

    # Unit name used for DB rows (joins with AxisCodingFitMetrics). Should
    # match the original AxisCodingAnalysis run — typically "Cluster".
    # Set write_to_db=False to skip the upserts entirely.
    unit_name = "Cluster"
    write_to_db = True

    # ----------------------------------------------------------------------

    save_dir = os.path.abspath(save_dir)
    if not os.path.isdir(save_dir):
        raise FileNotFoundError(f"save_dir not found: {save_dir}")

    json_paths = sorted(glob.glob(os.path.join(save_dir, "axis_coding_*.json")))
    if not json_paths:
        raise FileNotFoundError(f"No axis_coding_*.json in {save_dir}")

    print(f"[position_along_axis] {len(json_paths)} JSONs in {save_dir}")
    df = _prepare_session_df(session_id)

    repo_conn = None
    if write_to_db:
        try:
            from clat.util.connection import Connection
            repo_conn = Connection("allen_data_repository")
            print("[position_along_axis] db: writing to allen_data_repository")
        except Exception as exc:
            print(f"[position_along_axis] db: connection failed ({exc}); "
                  f"continuing without DB writes")
            repo_conn = None

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
                n_position_bins=n_position_bins,
                session_id=session_id,
                unit_name=unit_name,
                repo_conn=repo_conn,
            ) is not None:
                n_ok += 1
        except Exception as exc:
            print(f"  [error] {exc}")
            import traceback
            traceback.print_exc()

    print(f"\n[position_along_axis] done — {n_ok}/{len(json_paths)} figures written.")


if __name__ == "__main__":
    main()

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

CLI::

    python -m src.analysis.ga.axis_coding.position_along_axis \
        --save-dir /path/to/.../axis_coding \
        --session-id 260426_0 \
        [--top-orth 3] [--n-bins 9] [--z-range 2.0]
"""

from __future__ import annotations

import argparse
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
    phi_mean: np.ndarray           # circular mean
    mag_mean: np.ndarray           # ||mean(xyz)|| per bin (concentration)
    xyz_mean: np.ndarray           # (n_bins, 3) Cartesian mean position
    variance: Optional[float] = None  # axis variance (for orth axes)


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
    phi_mean = np.full(n_bins, np.nan)
    mag_mean = np.full(n_bins, np.nan)
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
        theta_mean[b] = float(np.arctan2(np.mean(np.sin(theta[sel])),
                                         np.mean(np.cos(theta[sel]))))
        phi_mean[b] = float(np.arctan2(np.mean(np.sin(phi[sel])),
                                       np.mean(np.cos(phi[sel]))))
        mean_xyz = xyz[sel].mean(axis=0)
        xyz_mean[b] = mean_xyz
        mag_mean[b] = float(np.linalg.norm(mean_xyz))

    return BinnedAxis(
        label=label,
        centers=centers,
        counts=counts,
        radial_mean=radial_mean,
        radial_sem=radial_sem,
        theta_mean=theta_mean,
        phi_mean=phi_mean,
        mag_mean=mag_mean,
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
        ncols=5,
        figsize=(20, 3.6 * n_rows),
        squeeze=False,
    )

    col_titles = [
        "radialPosition (mean ± SEM)",
        "angularPosition.theta (circular mean)",
        "angularPosition.phi (circular mean)",
        "‖mean position vector‖",
        "mean (x, y) per bin",
    ]

    # Shared colormap for arrows so adjacent bins are visually ordered.
    cmap = plt.get_cmap("viridis")

    for r, b in enumerate(rows):
        for c in range(5):
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
                ax.plot(b.centers, b.theta_mean, "o-", color="tab:orange")
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
                ax.plot(b.centers, b.phi_mean, "o-", color="tab:green")
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
                ax.plot(b.centers, b.mag_mean, "o-", color="tab:red")
                ax.set_ylim(bottom=0)
                ax.set_xlabel("axis projection (z)", fontsize=8)
            elif c == 4:
                # 2D top-down arrows from origin to mean (x, y) per bin,
                # color = bin position along axis. Arrow length = how
                # consistent a preferred location the bin agrees on.
                xy = b.xyz_mean[:, :2]
                finite = np.isfinite(xy).all(axis=1)
                if finite.any():
                    bin_idxs = np.arange(b.centers.size)[finite]
                    norm_idx = bin_idxs / max(b.centers.size - 1, 1)
                    for k, ci in zip(bin_idxs, norm_idx):
                        ax.annotate(
                            "",
                            xy=(xy[k, 0], xy[k, 1]),
                            xytext=(0, 0),
                            arrowprops=dict(
                                arrowstyle="->",
                                color=cmap(ci),
                                lw=1.5,
                            ),
                        )
                    if mu_decoded is not None:
                        try:
                            mu_r = float(mu_decoded.get("radialPosition", np.nan))
                            mu_t = float(mu_decoded["angularPosition.theta"])
                            mu_p = float(mu_decoded["angularPosition.phi"])
                            mu_x = mu_r * np.sin(mu_p) * np.cos(mu_t)
                            mu_y = mu_r * np.sin(mu_p) * np.sin(mu_t)
                            if np.isfinite([mu_x, mu_y]).all():
                                ax.scatter(
                                    [mu_x], [mu_y], marker="x", s=80,
                                    color="black", label="μ",
                                )
                                ax.legend(fontsize=7, loc="best")
                        except (KeyError, TypeError, ValueError):
                            pass
                    lim = float(np.nanmax(np.abs(xy[finite]))) * 1.2 or 1.0
                    ax.set_xlim(-lim, lim)
                    ax.set_ylim(-lim, lim)
                ax.axhline(0, color="lightgrey", lw=0.5, zorder=0)
                ax.axvline(0, color="lightgrey", lw=0.5, zorder=0)
                ax.set_aspect("equal", adjustable="box")
                ax.set_xlabel("x")
                ax.set_ylabel("y")

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

    fig.suptitle(title, fontsize=12)
    fig.tight_layout(rect=(0.02, 0, 1, 0.97))
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
                        label=f"orth#{rank + 1}",
                        n_bins=n_bins,
                        z_range=z_range,
                        axis_variance=float(all_orth_var[k]),
                    )
                )

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
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Visualize object-centered position along the preferred + top-N "
            "orthogonal axes from saved axis_coding_*.json model files."
        )
    )
    parser.add_argument(
        "--save-dir", required=True,
        help="Directory containing axis_coding_*.json files.",
    )
    parser.add_argument(
        "--session-id", required=True,
        help="Session id (e.g. '260426_0') used to fetch the source df.",
    )
    parser.add_argument("--top-orth", type=int, default=3)
    parser.add_argument("--n-bins", type=int, default=9)
    parser.add_argument("--z-range", type=float, default=2.0)
    args = parser.parse_args(argv)

    save_dir = os.path.abspath(args.save_dir)
    if not os.path.isdir(save_dir):
        print(f"--save-dir not found: {save_dir}", file=sys.stderr)
        return 2

    json_paths = sorted(glob.glob(os.path.join(save_dir, "axis_coding_*.json")))
    if not json_paths:
        print(f"No axis_coding_*.json in {save_dir}", file=sys.stderr)
        return 1

    print(f"[position_along_axis] {len(json_paths)} JSONs in {save_dir}")
    df = _prepare_session_df(args.session_id)

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
                top_orth=args.top_orth,
                n_bins=args.n_bins,
                z_range=args.z_range,
            ) is not None:
                n_ok += 1
        except Exception as exc:
            print(f"  [error] {exc}")
            import traceback
            traceback.print_exc()

    print(f"\n[position_along_axis] done — {n_ok}/{len(json_paths)} figures written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

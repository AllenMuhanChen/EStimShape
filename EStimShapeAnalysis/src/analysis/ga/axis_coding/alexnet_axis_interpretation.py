"""
Interpret an AlexNet preferred axis (and its orthogonal axes) in shape-
parameter space.

For each kept axis (preferred + top-N orthogonal), regress the per-stim
axis projection onto a shape-parameter design matrix. Per component type
(Shaft / Termination / Junction) we re-use the project's multi-prototype
attention selector to handle the multi-component-per-stim problem the
same way the geometry-parameterized axis-coding pipeline does — so each
stim contributes a single soft-pooled shape vector to the regression,
plus a learned prototype μ in shape-feature space that you can decode
and render as an exemplar.

Variance partition across the three types:
  - Marginal R²:   R²(S), R²(T), R²(J)
  - Joint R²:      R²(S|T), R²(S|J), R²(T|J), R²(S|T|J)
  - Commonality (3-way Venn) is computed for the preferred axis only;
    orthogonal axes report marginal R² only to keep the figure compact.

Output: ShapeInterpretationResult dataclass; the standalone driver
`interpret_alexnet_axes_with_shape(...)` builds it from an AxisCodingResult
+ the compiled df, saves a JSON dump and per-axis figures, and returns the
result for downstream inspection. The AlexNet analyzer can call this as an
opt-in post-fit step.
"""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from src.analysis.ga.axis_coding.axis_coding_analysis import (
    AxisCodingResult,
    _jsonable,
)
from src.analysis.ga.axis_coding.axis_coding_dataset import (
    AxisCodingDataset,
    _coerce_to_list_of_dicts,
)
from src.analysis.ga.axis_coding.component_encoding import (
    ComponentEncoder,
    PCAPreprocessor,
    make_default_encoders,
)
from src.analysis.ga.axis_coding.component_selectors import (
    MultiPrototypeAttentionSelector,
)
from src.analysis.ga.axis_coding.ridge_regression_model import (
    RidgeRegressionAxisModel,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class ShapeInterpretationConfig:
    """
    Hyperparams for the shape-space interpretation of an AlexNet axis.

    Defaults mirror the MultiPrototypeAttentionSelector setup used by
    ``axis_coding_analysis.make_default_strategies`` (``multi_prototype_pca``):
    K=2 prototypes, τ=1.0, λ_amp=0.1, and 6 PCs on the shape features. Tweak
    independently of the AlexNet pipeline's own strategies.
    """

    component_types: list[str] = field(
        default_factory=lambda: ["Shaft", "Termination", "Junction"]
    )
    top_n_orth_axes: int = 3
    # Object-centered position-along-axis plots — one figure per component
    # type, showing how the shape selector's chosen component's
    # radialPosition / angularPosition.theta / .phi varies along the
    # AlexNet preferred axis + top-N orth axes (binned by z-scored
    # projection). Reuses position_along_axis._bin_axis / _plot_figure.
    do_position_along_axis: bool = True
    position_top_n_orth: int = 3
    position_n_bins: int = 9
    position_z_range: float = 2.0
    # Per-PC × shape regression: how predictable each AlexNet PC is from
    # shape parameters. The PC set is the *union* of two picks: top-N by
    # PCA variance (general structure of the AlexNet representation) and
    # top-N by the preferred axis's loading magnitude (PCs the neuron
    # actually uses). With overlap, the union may be smaller than the sum.
    # Set ``do_pc_shape_fits=False`` to skip the panel entirely.
    do_pc_shape_fits: bool = True
    n_top_pcs_by_variance: int = 2
    n_top_pcs_by_preferred_axis_loading: int = 2

    # Match the shape pipeline's MultiPrototypeAttentionSelector + n_pcs.
    n_pcs: Optional[int] = 6
    n_prototypes: int = 2
    tau: float = 1.0
    alpha: float = 1.0
    lambda_amp: float = 0.1
    max_iter: int = 30
    tol: float = 1e-3
    init_jitter: float = 0.5
    amplitude_floor: float = 1e-3
    mu_optimizer_max_iter: int = 100

    # Ridge config (matches default_ridge_factory).
    ridge_alphas: tuple = field(
        default_factory=lambda: tuple(np.logspace(-3, 4, 20).tolist())
    )
    ridge_cv: int = 5
    ridge_n_splits_cv_r2: int = 20
    ridge_test_size: float = 0.2

    def make_selector(self) -> MultiPrototypeAttentionSelector:
        return MultiPrototypeAttentionSelector(
            n_prototypes=self.n_prototypes,
            tau=self.tau,
            alpha=self.alpha,
            lambda_amp=self.lambda_amp,
            max_iter=self.max_iter,
            tol=self.tol,
            init_jitter=self.init_jitter,
            amplitude_floor=self.amplitude_floor,
            mu_optimizer_max_iter=self.mu_optimizer_max_iter,
        )

    def make_ridge(self) -> RidgeRegressionAxisModel:
        return RidgeRegressionAxisModel(
            alphas=np.asarray(self.ridge_alphas, dtype=np.float64),
            cv=self.ridge_cv,
            n_splits_cv_r2=self.ridge_n_splits_cv_r2,
            test_size=self.ridge_test_size,
        )


# ---------------------------------------------------------------------------
# Per-(axis, type) fit record
# ---------------------------------------------------------------------------

@dataclass
class PerTypeAxisFit:
    component_type: str
    axis_name: str
    n_stim: int
    feature_names: list[str]              # original shape-feature names (d_shape,)
    cv_r2_mean: float
    cv_r2_std: float
    train_r2: float
    ridge_alpha: float
    ridge_coefs_orig: list[float]         # back-projected (d_shape,) if PCA, else (d_shape,)
    ridge_intercept: float
    prototype_mu_unscaled: list[float]                  # primary μ in raw shape-feature units
    prototype_mu_decoded: dict                          # encoder.decode_to_parameters
    prototypes_mus_unscaled: list[list[float]]          # all K prototypes
    prototypes_mus_decoded: list[dict]
    prototype_amplitudes: Optional[list[float]] = None
    pca_explained_variance: Optional[list[float]] = None
    selector_summary: Optional[dict] = None
    stim_ids: Optional[list] = None                     # stim_ids used in this fit
    # Hard-selected component index per stim (aligned with ``stim_ids``) from
    # the MultiPrototypeAttentionSelector — i.e. which Shaft/Termination/
    # Junction the selector chose to represent each stim. Used by the
    # object-centered position-along-axis plot so it can pull the chosen
    # component's radialPosition / angularPosition.theta / .phi.
    selected_indices: Optional[list[int]] = None


@dataclass
class VariancePartition:
    axis_name: str
    n_stim_intersection: int
    marginal_r2: dict[str, float]                       # {type: cv_r2}
    joint_r2: dict[str, float]                          # keys like "Shaft+Termination"
    # Commonality decomposition (3-way Venn). Keys:
    #   "unique_Shaft", "unique_Termination", "unique_Junction",
    #   "shared_S∩T", "shared_S∩J", "shared_T∩J", "shared_S∩T∩J"
    # Populated only when all three types are present; None otherwise (e.g.
    # orth axes with marginal_only=True).
    commonality: Optional[dict[str, float]] = None


@dataclass
class ShapeInterpretationResult:
    config: dict
    primary_axis_name: str
    axis_fits: dict[str, dict[str, PerTypeAxisFit]]      # {axis_name: {type: fit}}
    variance_partitions: dict[str, VariancePartition]   # {axis_name: partition}
    # Per-PC × per-type fits answering "how predictable is each AlexNet PC
    # from shape parameters". Keys like "PC_1", "PC_2", ... aligned with
    # the indices of the top-N PCs by explained variance.
    pc_fits: dict[str, dict[str, PerTypeAxisFit]] = field(default_factory=dict)
    # Convenience: PCA explained-variance ratio copied from the source
    # AxisCodingResult so the summary plot has everything it needs in one
    # place when loaded from JSON.
    pca_explained_variance: Optional[list[float]] = None
    # PC-space weights of preferred + each kept orth axis, copied from the
    # source AxisCodingResult; used by the summary plot's "axis energy per
    # PC" panel.
    preferred_axis_pc_weights: Optional[list[float]] = None
    orth_axes_pc_weights: Optional[list[list[float]]] = None         # (k, n_orth)
    orth_axes_pc_variances: Optional[list[float]] = None             # (n_orth,)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def interpret_alexnet_axes_with_shape(
    result: AxisCodingResult,
    df: pd.DataFrame,
    *,
    config: Optional[ShapeInterpretationConfig] = None,
    encoders: Optional[dict[str, ComponentEncoder]] = None,
    save_dir: Optional[str] = None,
    save_prefix: str = "alexnet_shape_interp",
    title_prefix: str = "",
    show_plots: bool = True,
) -> ShapeInterpretationResult:
    """
    Run the shape-parameter interpretation pipeline on one AlexNet
    AxisCodingResult.

    For the preferred axis we run per-type fits + full 3-way commonality
    variance partition. For each of the top ``config.top_n_orth_axes``
    orthogonal axes (ranked by all_orthogonal_variances) we run the same
    per-type fits but report marginal R² only.

    Side effects when ``save_dir`` is set: writes ``<save_prefix>.json`` plus
    one figure per axis.
    """
    config = config or ShapeInterpretationConfig()
    encoders = encoders or make_default_encoders()

    if result.axis_projections is None:
        raise ValueError(
            "AxisCodingResult.axis_projections is None — cannot interpret."
        )

    # Axis list: preferred + top-N orth by variance.
    axes_to_fit: list[tuple[str, np.ndarray, bool]] = []  # (name, proj, do_commonality)
    axes_to_fit.append(
        ("preferred",
         np.asarray(result.axis_projections, dtype=np.float64),
         True)
    )
    if (result.all_orthogonal_projections is not None
            and result.all_orthogonal_variances is not None
            and config.top_n_orth_axes > 0):
        orth_projs = np.asarray(
            result.all_orthogonal_projections, dtype=np.float64
        )  # (N, n_orth)
        orth_vars = np.asarray(
            result.all_orthogonal_variances, dtype=np.float64
        )  # (n_orth,)
        # Rank orth axes by variance, take top N (or fewer if not enough).
        order = np.argsort(-orth_vars)[: config.top_n_orth_axes]
        for rank, j in enumerate(order):
            axes_to_fit.append(
                (f"orth_{rank + 1}", orth_projs[:, int(j)], False)
            )

    axis_fits: dict[str, dict[str, PerTypeAxisFit]] = {}
    variance_partitions: dict[str, VariancePartition] = {}

    # Stim ids the result was fit on, in order. Axis projections align 1:1.
    # result.stim_ids round-trips through _jsonable, which falls through to
    # str(x) for plain Python ints — so they end up as strings while the
    # df's StimSpecId column is integer. Filter via stringified compare so
    # the mismatch can't drop every row silently.
    result_stim_ids = list(result.stim_ids)
    result_stim_ids_str = {str(s) for s in result_stim_ids}

    # Build a quick stim-grouped df once; we re-use it for each (axis, type).
    df_for_stims = df[df["StimSpecId"].astype(str).isin(result_stim_ids_str)].copy()
    if df_for_stims.empty:
        raise RuntimeError(
            f"After filtering df to result.stim_ids, zero rows remained. "
            f"Result has {len(result_stim_ids)} stim_ids (e.g. "
            f"{result_stim_ids[:3]}); df has {len(df)} rows with "
            f"StimSpecId examples "
            f"{df['StimSpecId'].head(3).tolist() if 'StimSpecId' in df.columns else 'MISSING'}. "
            f"Check that you're passing the right df (compiled for the "
            f"same session as the saved result)."
        )
    print(
        f"[shape-interp] df filtered to {len(df_for_stims)} rows for "
        f"{len(result_stim_ids)} stim_ids "
        f"({df_for_stims['StimSpecId'].nunique()} unique)."
    )

    for axis_name, proj_per_stim, do_commonality in axes_to_fit:
        if proj_per_stim.shape[0] != len(result_stim_ids):
            raise RuntimeError(
                f"Axis '{axis_name}' projection length "
                f"({proj_per_stim.shape[0]}) does not match stim_ids "
                f"({len(result_stim_ids)})."
            )

        per_type: dict[str, PerTypeAxisFit] = {}
        per_type_design: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        # value = (stim_ids_for_type, X_pooled (N_t, d_or_k), target (N_t,))

        for comp_type in config.component_types:
            if comp_type not in df_for_stims.columns:
                print(f"  [shape-interp] {axis_name}/{comp_type}: column missing, skipping")
                continue
            encoder = ComponentEncoder(
                linear_params=list(encoders[comp_type].linear_params),
                circular_params=list(encoders[comp_type].circular_params),
                spherical_params=list(encoders[comp_type].spherical_params),
            )
            fit_out = _fit_per_type_axis(
                df_for_stims,
                stim_ids=result_stim_ids,
                axis_projections=proj_per_stim,
                component_type=comp_type,
                encoder=encoder,
                config=config,
                axis_name=axis_name,
            )
            if fit_out is None:
                continue
            fit_rec, X_pool, target, stim_ids_used = fit_out
            per_type[comp_type] = fit_rec
            per_type_design[comp_type] = (
                np.asarray(stim_ids_used), X_pool, target,
            )

        axis_fits[axis_name] = per_type

        # Variance partition across the per-type designs.
        partition = _variance_partition(
            per_type_design,
            axis_name=axis_name,
            do_commonality=do_commonality,
            config=config,
        )
        variance_partitions[axis_name] = partition

        # Per-axis figure.
        if save_dir is not None or show_plots:
            fig = _plot_axis_interpretation(
                axis_name=axis_name,
                per_type=per_type,
                partition=partition,
                config=config,
                title_prefix=title_prefix,
            )
            if fig is not None and save_dir is not None:
                os.makedirs(save_dir, exist_ok=True)
                fig_path = os.path.join(
                    save_dir, f"{save_prefix}_{axis_name}.png"
                )
                fig.savefig(fig_path, dpi=150, bbox_inches="tight")
                print(f"  [shape-interp] saved: {fig_path}")
            if fig is not None:
                if show_plots:
                    plt.show()
                else:
                    plt.close(fig)

    # Per-PC × per-type shape regression. Tells you, for each of the top-N
    # AlexNet PCs (by explained variance), how well shape parameters of
    # each component type predict the PC's scores. Skipped if the result
    # JSON has no PC scores (PCA wasn't active, or the result was produced
    # before pc_scores_per_stim was added).
    pc_fits: dict[str, dict[str, PerTypeAxisFit]] = {}
    if (
        config.do_pc_shape_fits
        and result.pc_scores_per_stim is not None
        and result.pca_explained_variance is not None
        and (config.n_top_pcs_by_variance
             + config.n_top_pcs_by_preferred_axis_loading) > 0
    ):
        pc_fits = _run_pc_shape_fits(
            result=result,
            df_for_stims=df_for_stims,
            result_stim_ids=result_stim_ids,
            encoders=encoders,
            config=config,
        )
    elif config.do_pc_shape_fits:
        msg = (
            "[shape-interp] PC × shape fits skipped: "
            f"pc_scores_per_stim is {'set' if result.pc_scores_per_stim is not None else 'None'}; "
            f"pca_explained_variance is {'set' if result.pca_explained_variance is not None else 'None'}."
        )
        if result.pc_scores_per_stim is None:
            msg += (
                "  Re-run AlexNetAxisCodingAnalysis on this session to "
                "regenerate the result JSON (older JSONs don't have "
                "pc_scores_per_stim populated)."
            )
        print(msg)

    out = ShapeInterpretationResult(
        config=dataclasses.asdict(config),
        primary_axis_name="preferred",
        axis_fits=axis_fits,
        variance_partitions=variance_partitions,
        pc_fits=pc_fits,
        pca_explained_variance=list(result.pca_explained_variance)
            if result.pca_explained_variance is not None else None,
        preferred_axis_pc_weights=(
            list(result.ridge_summary.get("weights"))
            if (result.ridge_summary is not None
                and result.ridge_summary.get("weights") is not None)
            else None
        ),
        orth_axes_pc_weights=(
            list(result.all_orthogonal_axes)
            if result.all_orthogonal_axes is not None else None
        ),
        orth_axes_pc_variances=(
            list(result.all_orthogonal_variances)
            if result.all_orthogonal_variances is not None else None
        ),
    )

    # Object-centered position along axis: per component type, render the
    # binned-mean of the shape selector's chosen component's
    # radialPosition / angularPosition along the AlexNet preferred axis and
    # the top-N orth axes. Selection comes from the preferred-axis fit so
    # all axes share one set of "chosen components" per stim.
    if config.do_position_along_axis and "preferred" in axis_fits:
        try:
            _plot_position_along_alexnet_axes(
                axis_fits_preferred=axis_fits["preferred"],
                df_for_stims=df_for_stims,
                result=result,
                result_stim_ids=result_stim_ids,
                config=config,
                save_dir=save_dir,
                save_prefix=save_prefix,
                title_prefix=title_prefix,
                show_plots=show_plots,
            )
        except Exception as exc:
            import traceback
            print(f"  [shape-interp] position-along-axis FAILED: {exc}")
            traceback.print_exc()

    # Comprehensive summary figure: scree + per-axis PC energy + per-PC
    # shape predictability heatmap + per-axis shape predictability bars.
    if save_dir is not None or show_plots:
        fig_sum = _plot_pc_summary(
            out, title_prefix=title_prefix,
        )
        if fig_sum is not None and save_dir is not None:
            os.makedirs(save_dir, exist_ok=True)
            sum_path = os.path.join(save_dir, f"{save_prefix}_summary.png")
            fig_sum.savefig(sum_path, dpi=150, bbox_inches="tight")
            print(f"  [shape-interp] saved: {sum_path}")
        if fig_sum is not None:
            if show_plots:
                plt.show()
            else:
                plt.close(fig_sum)

    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        json_path = os.path.join(save_dir, f"{save_prefix}.json")
        with open(json_path, "w") as f:
            json.dump(_result_to_jsonable(out), f, indent=2, default=_jsonable)
        print(f"  [shape-interp] saved: {json_path}")

    return out


# ---------------------------------------------------------------------------
# Per-(axis, type) fit
# ---------------------------------------------------------------------------

def _fit_per_type_axis(
    df: pd.DataFrame,
    *,
    stim_ids: list,
    axis_projections: np.ndarray,
    component_type: str,
    encoder: ComponentEncoder,
    config: ShapeInterpretationConfig,
    axis_name: str,
) -> Optional[tuple[PerTypeAxisFit, np.ndarray, np.ndarray, list]]:
    """
    Build a per-component-type shape dataset for one axis, fit the multi-
    prototype attention selector (with axis projection as the target), then
    fit ridge on the soft-pooled selected vectors and report loadings + μ.

    Returns (fit_record, X_pooled (N_t, d_or_k), target (N_t,), stim_ids_used)
    or ``None`` if no stims have components for this type.
    """
    # result.stim_ids comes through _jsonable, which falls through to str(x)
    # for plain Python ints — so result.stim_ids is a list of strings whereas
    # the df's StimSpecId is integers. Normalize both sides via str(...) so
    # the lookup matches regardless of upstream typing.
    proj_by_stim = {str(s): float(p) for s, p in zip(stim_ids, axis_projections.tolist())}

    df_local = df.copy()
    df_local[component_type] = df_local[component_type].apply(_coerce_to_list_of_dicts)
    per_stim_components = df_local.groupby("StimSpecId")[component_type].first()

    kept_stim_ids: list = []
    kept_components: list[list[dict]] = []
    kept_responses: list[float] = []
    n_no_proj = 0
    n_empty_components = 0
    for raw_sid, comps in per_stim_components.items():
        sid_key = str(raw_sid)
        if sid_key not in proj_by_stim:
            n_no_proj += 1
            continue
        if comps is None or (isinstance(comps, list) and len(comps) == 0):
            n_empty_components += 1
            continue
        kept_stim_ids.append(raw_sid)
        kept_components.append(comps)
        kept_responses.append(proj_by_stim[sid_key])

    print(
        f"  [shape-interp] {axis_name}/{component_type}: "
        f"matched={len(kept_stim_ids)}  "
        f"no_projection={n_no_proj}  empty_components={n_empty_components}  "
        f"(input stim_ids={len(proj_by_stim)})"
    )

    if not kept_stim_ids:
        print(f"  [shape-interp] {axis_name}/{component_type}: no stims with components")
        return None

    encoded_per_stim = [encoder.encode_components(c) for c in kept_components]
    valid = [
        (e, r, s) for e, r, s in zip(encoded_per_stim, kept_responses, kept_stim_ids)
        if e.shape[0] > 0
    ]
    if not valid:
        print(f"  [shape-interp] {axis_name}/{component_type}: no encodable components")
        return None
    encoded_per_stim, kept_responses, kept_stim_ids = map(list, zip(*valid))
    all_components = np.vstack(encoded_per_stim)
    encoder.fit_scaler(all_components)
    scaled_per_stim = [encoder.transform_with_scaler(e) for e in encoded_per_stim]
    responses = np.asarray(kept_responses, dtype=np.float64)

    # Optional PCA on the shape features (mirrors the multi_prototype_pca strategy).
    pca_pre: Optional[PCAPreprocessor] = None
    if config.n_pcs is not None and config.n_pcs > 0:
        pca_pre = PCAPreprocessor(n_components=config.n_pcs)
        components_for_selector = pca_pre.fit_transform(scaled_per_stim)
    else:
        components_for_selector = scaled_per_stim

    selector = config.make_selector()
    selector.fit(components_for_selector, responses)
    X_pool = selector.selected_vectors(components_for_selector)  # (N_t, k_or_d)

    ridge = config.make_ridge()
    # Use PC names if PCA was applied; the original feature_names live on the encoder.
    feat_names_for_ridge = (
        pca_pre.pc_feature_names() if pca_pre is not None else list(encoder.feature_names)
    )
    ridge.fit(X_pool, responses, feature_names=feat_names_for_ridge)

    # Back-project ridge weights and prototype μ to original feature space.
    w_pc = np.asarray(ridge.w_, dtype=np.float64)
    if pca_pre is not None:
        w_orig = pca_pre.back_project(w_pc)
    else:
        w_orig = w_pc.copy()

    mu_primary_unscaled, mu_primary_decoded = _decode_mu(
        selector.mu_, pca_pre, encoder,
    )
    mus_unscaled: list[list[float]] = []
    mus_decoded: list[dict] = []
    if selector.mus_ is not None:
        for k in range(selector.mus_.shape[0]):
            u, d = _decode_mu(selector.mus_[k], pca_pre, encoder)
            mus_unscaled.append(u.tolist())
            mus_decoded.append(d)

    fit_rec = PerTypeAxisFit(
        component_type=component_type,
        axis_name=axis_name,
        n_stim=len(kept_stim_ids),
        feature_names=list(encoder.feature_names),
        cv_r2_mean=ridge.cv_r2_mean_ if ridge.cv_r2_mean_ is not None else float("nan"),
        cv_r2_std=ridge.cv_r2_std_ if ridge.cv_r2_std_ is not None else float("nan"),
        train_r2=ridge.train_r2_ if ridge.train_r2_ is not None else float("nan"),
        ridge_alpha=ridge.alpha_ if ridge.alpha_ is not None else float("nan"),
        ridge_coefs_orig=w_orig.tolist(),
        ridge_intercept=ridge.intercept_ if ridge.intercept_ is not None else 0.0,
        prototype_mu_unscaled=mu_primary_unscaled.tolist(),
        prototype_mu_decoded=mu_primary_decoded,
        prototypes_mus_unscaled=mus_unscaled,
        prototypes_mus_decoded=mus_decoded,
        prototype_amplitudes=(
            selector.amplitudes_.tolist()
            if selector.amplitudes_ is not None else None
        ),
        pca_explained_variance=(
            pca_pre.explained_variance_ratio.tolist()
            if pca_pre is not None else None
        ),
        selector_summary=selector.summary(components_for_selector),
        stim_ids=[_jsonable(s) for s in kept_stim_ids],
        selected_indices=(
            [int(i) for i in selector.selected_indices_]
            if selector.selected_indices_ is not None else None
        ),
    )

    cv = fit_rec.cv_r2_mean
    cv_str = f"{cv:+.3f}" if cv == cv else "n/a"  # nan-safe
    print(
        f"  [shape-interp] {axis_name}/{component_type}: "
        f"n={fit_rec.n_stim}  d={X_pool.shape[1]}  cv_r2={cv_str}"
    )

    return fit_rec, X_pool, responses, kept_stim_ids


def _decode_mu(
    mu_selector_space: Optional[np.ndarray],
    pca_pre: Optional[PCAPreprocessor],
    encoder: ComponentEncoder,
) -> tuple[np.ndarray, dict]:
    """
    Back-project μ from selector space (PC if PCA used) to raw shape-feature
    units and decode to the interpretable parameter dict.
    """
    if mu_selector_space is None:
        return np.zeros(encoder.n_features, dtype=np.float64), {}
    if pca_pre is not None:
        feat_z = pca_pre.back_project(np.asarray(mu_selector_space, dtype=np.float64))
    else:
        feat_z = np.asarray(mu_selector_space, dtype=np.float64)
    unscaled = encoder.inverse_scale(feat_z)
    return unscaled, encoder.decode_to_parameters(unscaled)


# ---------------------------------------------------------------------------
# Variance partition (3-way commonality decomposition)
# ---------------------------------------------------------------------------

# Keys for the commonality output. C(STJ) sums to R²(STJ).
_COMMONALITY_LABELS = (
    "unique_Shaft",
    "unique_Termination",
    "unique_Junction",
    "shared_S∩T",
    "shared_S∩J",
    "shared_T∩J",
    "shared_S∩T∩J",
)


def _variance_partition(
    per_type_design: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    axis_name: str,
    do_commonality: bool,
    config: ShapeInterpretationConfig,
) -> VariancePartition:
    """
    Fit ridge on every non-empty subset of component types over the
    stim-id intersection where all relevant types have a design row,
    then assemble the commonality decomposition.
    """
    types = list(per_type_design.keys())
    if not types:
        return VariancePartition(
            axis_name=axis_name,
            n_stim_intersection=0,
            marginal_r2={},
            joint_r2={},
            commonality=None,
        )

    # Intersection of stim_ids across types (only those that have a design row
    # in every requested type — required for joint models to be well-defined).
    stim_sets = [set(per_type_design[t][0].tolist()) for t in types]
    common = set.intersection(*stim_sets) if stim_sets else set()
    if not common:
        print(
            f"  [shape-interp] {axis_name}: no stim_id intersection across "
            f"types {types}; skipping variance partition."
        )
        return VariancePartition(
            axis_name=axis_name,
            n_stim_intersection=0,
            marginal_r2={t: _fit_subset_r2(per_type_design, [t], None, config)
                         for t in types},
            joint_r2={},
            commonality=None,
        )

    # All subsets of size >= 1.
    marginal: dict[str, float] = {}
    joint: dict[str, float] = {}
    subset_r2: dict[frozenset, float] = {}
    n_intersect = len(common)
    for r in range(1, len(types) + 1):
        for subset in _combinations(types, r):
            r2 = _fit_subset_r2(per_type_design, list(subset), common, config)
            key = "+".join(subset)
            subset_r2[frozenset(subset)] = r2
            if r == 1:
                marginal[subset[0]] = r2
            else:
                joint[key] = r2

    commonality = None
    if do_commonality and len(types) == 3 and all(
        t in per_type_design for t in ("Shaft", "Termination", "Junction")
    ):
        commonality = _commonality_3way(subset_r2)

    return VariancePartition(
        axis_name=axis_name,
        n_stim_intersection=n_intersect,
        marginal_r2=marginal,
        joint_r2=joint,
        commonality=commonality,
    )


def _fit_subset_r2(
    per_type_design: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    subset: list[str],
    common: Optional[set],
    config: ShapeInterpretationConfig,
) -> float:
    """
    Concatenate the per-type X blocks for ``subset`` over a common stim-id
    intersection (or each block's own stims when ``common`` is None for the
    marginal-only fallback) and fit ridge → return CV R².
    """
    blocks: list[np.ndarray] = []
    target: Optional[np.ndarray] = None
    for t in subset:
        stim_arr, X_t, r_t = per_type_design[t]
        if common is not None:
            mask = np.isin(stim_arr, np.asarray(list(common)))
            order = np.argsort(stim_arr[mask])
            X_use = X_t[mask][order]
            r_use = r_t[mask][order]
        else:
            order = np.argsort(stim_arr)
            X_use = X_t[order]
            r_use = r_t[order]
        blocks.append(X_use)
        target = r_use if target is None else target
        if r_use.shape != target.shape or not np.allclose(r_use, target):
            # When ``common`` is set, targets must match across types after
            # sorting by stim_id. If they don't, the per_type_design has
            # an alignment bug — fail loudly rather than silently regress.
            raise RuntimeError(
                f"Per-type targets disagree on the shared stims for subset "
                f"{subset}. This is a bug."
            )

    if target is None or target.shape[0] < 5:
        return float("nan")
    X = np.column_stack(blocks)
    ridge = config.make_ridge()
    ridge.fit(X, target)
    return (
        ridge.cv_r2_mean_ if ridge.cv_r2_mean_ is not None
        else float("nan")
    )


def _commonality_3way(subset_r2: dict[frozenset, float]) -> dict[str, float]:
    """
    Standard 3-way commonality decomposition for predictors {S, T, J}:

        U(S) = R²(STJ) - R²(TJ)
        U(T) = R²(STJ) - R²(SJ)
        U(J) = R²(STJ) - R²(ST)
        C(ST)  = R²(SJ) + R²(TJ) - R²(J) - R²(STJ)
        C(SJ)  = R²(ST) + R²(TJ) - R²(T) - R²(STJ)
        C(TJ)  = R²(ST) + R²(SJ) - R²(S) - R²(STJ)
        C(STJ) = R²(S) + R²(T) + R²(J)
                 - R²(ST) - R²(SJ) - R²(TJ)
                 + R²(STJ)

    Sum equals R²(STJ). Individual values can be negative when predictors
    are correlated and one suppresses another — that is meaningful, not a
    bug, so we report it as-is.
    """
    S = frozenset({"Shaft"})
    T = frozenset({"Termination"})
    J = frozenset({"Junction"})
    ST = frozenset({"Shaft", "Termination"})
    SJ = frozenset({"Shaft", "Junction"})
    TJ = frozenset({"Termination", "Junction"})
    STJ = frozenset({"Shaft", "Termination", "Junction"})

    def g(k):
        v = subset_r2.get(k)
        return float("nan") if v is None else float(v)

    r_S, r_T, r_J = g(S), g(T), g(J)
    r_ST, r_SJ, r_TJ = g(ST), g(SJ), g(TJ)
    r_STJ = g(STJ)

    return {
        "unique_Shaft": r_STJ - r_TJ,
        "unique_Termination": r_STJ - r_SJ,
        "unique_Junction": r_STJ - r_ST,
        "shared_S∩T": r_SJ + r_TJ - r_J - r_STJ,
        "shared_S∩J": r_ST + r_TJ - r_T - r_STJ,
        "shared_T∩J": r_ST + r_SJ - r_S - r_STJ,
        "shared_S∩T∩J": (
            r_S + r_T + r_J - r_ST - r_SJ - r_TJ + r_STJ
        ),
        "_total_R2_STJ": r_STJ,
    }


def _combinations(items: list, r: int):
    """Yield r-subsets preserving input order (Python's itertools.combinations
    re-imported here so this module has no implicit ``itertools`` dependency
    leak in the dataclass globals.)"""
    from itertools import combinations
    yield from combinations(items, r)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _plot_axis_interpretation(
    *,
    axis_name: str,
    per_type: dict[str, PerTypeAxisFit],
    partition: VariancePartition,
    config: ShapeInterpretationConfig,
    title_prefix: str,
) -> Optional[plt.Figure]:
    """
    One figure per axis: per-type bar charts of top loadings + a variance-
    partition panel (commonality bars for the preferred axis, marginal-only
    bars for orth axes).
    """
    if not per_type:
        print(
            f"  [shape-interp] {axis_name}: no per-type fits to plot; "
            f"figure skipped."
        )
        return None

    types = [t for t in config.component_types if t in per_type]
    n_types = len(types)
    if n_types == 0:
        print(
            f"  [shape-interp] {axis_name}: 0 of "
            f"{len(config.component_types)} requested types fit; "
            f"figure skipped."
        )
        return None

    n_cols = n_types + 1  # one per type + one for variance partition
    fig, axes = plt.subplots(1, n_cols, figsize=(4.5 * n_cols, 5.0))
    if n_cols == 1:
        axes = np.array([axes])

    # Per-type top-loading bars.
    for ax, comp_type in zip(axes[:n_types], types):
        fit = per_type[comp_type]
        w = np.asarray(fit.ridge_coefs_orig, dtype=np.float64)
        names = fit.feature_names
        if w.size == 0:
            ax.set_visible(False)
            continue
        k = min(10, w.size)
        top = np.argsort(-np.abs(w))[:k]
        ax.barh(
            np.arange(k)[::-1],
            w[top],
            color=["#3a7bd5" if v >= 0 else "#d54848" for v in w[top]],
        )
        ax.set_yticks(np.arange(k)[::-1])
        ax.set_yticklabels([names[i] for i in top], fontsize=8)
        ax.axvline(0, color="k", lw=0.5)
        cv = fit.cv_r2_mean
        cv_str = f"{cv:+.3f}" if cv == cv else "n/a"
        ax.set_title(
            f"{comp_type}\nCV R²={cv_str}  n={fit.n_stim}",
            fontsize=10,
        )
        ax.tick_params(axis="x", labelsize=8)

    # Variance partition panel.
    ax_v = axes[n_types]
    if partition.commonality is not None:
        labels = [
            "unique_Shaft", "unique_Termination", "unique_Junction",
            "shared_S∩T", "shared_S∩J", "shared_T∩J", "shared_S∩T∩J",
        ]
        vals = [partition.commonality.get(k, 0.0) for k in labels]
        colors = ["#3a7bd5", "#3ad58b", "#d57b3a",
                  "#a06bff", "#c2b13a", "#3ac2b1", "#aaaaaa"]
        ax_v.barh(np.arange(len(labels))[::-1], vals, color=colors)
        ax_v.set_yticks(np.arange(len(labels))[::-1])
        ax_v.set_yticklabels(labels, fontsize=8)
        ax_v.axvline(0, color="k", lw=0.5)
        tot = partition.commonality.get("_total_R2_STJ", float("nan"))
        ax_v.set_title(
            f"variance partition\n"
            f"R²(S+T+J)={tot:+.3f}  n_int={partition.n_stim_intersection}",
            fontsize=10,
        )
    else:
        # Marginal-only fallback.
        items = list(partition.marginal_r2.items())
        if not items:
            ax_v.set_visible(False)
        else:
            names_m, vals = zip(*items)
            ax_v.barh(np.arange(len(vals))[::-1], vals, color="#3a7bd5")
            ax_v.set_yticks(np.arange(len(vals))[::-1])
            ax_v.set_yticklabels(names_m, fontsize=8)
            ax_v.axvline(0, color="k", lw=0.5)
            ax_v.set_title(
                f"marginal CV R²\nn_int={partition.n_stim_intersection}",
                fontsize=10,
            )
    ax_v.tick_params(axis="x", labelsize=8)

    title = (
        f"{title_prefix}  shape-space interpretation — {axis_name}"
        if title_prefix else
        f"shape-space interpretation — {axis_name}"
    )
    fig.suptitle(title, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _result_to_jsonable(out: ShapeInterpretationResult) -> dict:
    return {
        "config": out.config,
        "primary_axis_name": out.primary_axis_name,
        "axis_fits": {
            axis_name: {
                t: dataclasses.asdict(fit) for t, fit in per_type.items()
            }
            for axis_name, per_type in out.axis_fits.items()
        },
        "variance_partitions": {
            axis_name: dataclasses.asdict(vp)
            for axis_name, vp in out.variance_partitions.items()
        },
        "pc_fits": {
            pc_name: {
                t: dataclasses.asdict(fit) for t, fit in per_type.items()
            }
            for pc_name, per_type in out.pc_fits.items()
        },
        "pca_explained_variance": out.pca_explained_variance,
        "preferred_axis_pc_weights": out.preferred_axis_pc_weights,
        "orth_axes_pc_weights": out.orth_axes_pc_weights,
        "orth_axes_pc_variances": out.orth_axes_pc_variances,
    }


# ---------------------------------------------------------------------------
# Per-PC × shape fits (panel C in the summary plot)
# ---------------------------------------------------------------------------

def _run_pc_shape_fits(
    *,
    result: AxisCodingResult,
    df_for_stims: pd.DataFrame,
    result_stim_ids: list,
    encoders: dict[str, ComponentEncoder],
    config: ShapeInterpretationConfig,
) -> dict[str, dict[str, PerTypeAxisFit]]:
    """
    For a union of top PCs (top-N by variance + top-N by preferred-axis
    loading), fit the per-component-type attention+ridge pipeline with the
    PC's per-stim scores as the target. Yields a {pc_name: {type: fit}}
    dict.

    Two pick criteria, unioned (so a PC heavily loaded by the preferred
    axis is included even if it's far down the variance list, and vice
    versa):
      - top ``n_top_pcs_by_variance`` by explained variance ratio.
      - top ``n_top_pcs_by_preferred_axis_loading`` by |w_pref_i|.
    """
    pc_scores = np.asarray(result.pc_scores_per_stim, dtype=np.float64)  # (n_stim, k)
    if pc_scores.ndim != 2 or pc_scores.shape[0] != len(result_stim_ids):
        print(
            f"[shape-interp] PC × shape fits: pc_scores shape {pc_scores.shape} "
            f"doesn't match {len(result_stim_ids)} stims; skipping."
        )
        return {}

    explained = np.asarray(result.pca_explained_variance, dtype=np.float64)
    k_actual = min(pc_scores.shape[1], explained.shape[0])
    if k_actual == 0:
        return {}

    # Top-N by variance (sklearn PCs are already variance-sorted).
    n_var = max(0, min(int(config.n_top_pcs_by_variance), k_actual))
    idx_by_var = list(range(n_var))

    # Top-N by preferred-axis loading magnitude.
    n_pref = max(0, min(int(config.n_top_pcs_by_preferred_axis_loading), k_actual))
    idx_by_pref: list[int] = []
    pref_w = (
        result.ridge_summary.get("weights")
        if result.ridge_summary is not None else None
    )
    if n_pref > 0 and pref_w is not None and len(pref_w) >= k_actual:
        w_abs = np.abs(np.asarray(pref_w[:k_actual], dtype=np.float64))
        order = np.argsort(-w_abs)
        idx_by_pref = [int(i) for i in order[:n_pref]]
    elif n_pref > 0:
        print(
            "[shape-interp] preferred-axis loadings unavailable; "
            "falling back to variance-only PC selection."
        )

    # Union preserving variance-sorted order so the heatmap reads left→right
    # from "highest-variance" toward "preferred-axis-favorite".
    pc_indices_set = set(idx_by_var) | set(idx_by_pref)
    pc_indices = sorted(pc_indices_set)
    print(
        f"[shape-interp] PC × shape fits on {len(pc_indices)} PC(s): "
        f"by-variance={idx_by_var}  by-preferred-loading={idx_by_pref}"
    )

    pc_fits: dict[str, dict[str, PerTypeAxisFit]] = {}
    for pc_idx in pc_indices:
        pc_name = f"PC_{pc_idx + 1}"
        target = pc_scores[:, pc_idx]
        per_type: dict[str, PerTypeAxisFit] = {}
        for comp_type in config.component_types:
            if comp_type not in df_for_stims.columns:
                continue
            encoder = ComponentEncoder(
                linear_params=list(encoders[comp_type].linear_params),
                circular_params=list(encoders[comp_type].circular_params),
                spherical_params=list(encoders[comp_type].spherical_params),
            )
            fit_out = _fit_per_type_axis(
                df_for_stims,
                stim_ids=result_stim_ids,
                axis_projections=target,
                component_type=comp_type,
                encoder=encoder,
                config=config,
                axis_name=pc_name,
            )
            if fit_out is None:
                continue
            fit_rec, _Xp, _t, _sids = fit_out
            per_type[comp_type] = fit_rec
        if per_type:
            pc_fits[pc_name] = per_type
    return pc_fits


# ---------------------------------------------------------------------------
# Object-centered position along axis (per component type)
# ---------------------------------------------------------------------------

def _plot_position_along_alexnet_axes(
    *,
    axis_fits_preferred: dict,
    df_for_stims: pd.DataFrame,
    result: AxisCodingResult,
    result_stim_ids: list,
    config: ShapeInterpretationConfig,
    save_dir: Optional[str],
    save_prefix: str,
    title_prefix: str,
    show_plots: bool,
) -> None:
    """
    Reuse ``position_along_axis._extract_positions / _bin_axis / _plot_figure``
    against the AlexNet preferred + top-N orth axes, with each component
    type's per-stim selection coming from that type's preferred-axis fit
    (the shape selector trained against the AlexNet preferred axis).

    One figure per component type. Skipped silently for any type whose
    preferred-axis fit failed (no selection to bin against).
    """
    from src.analysis.ga.axis_coding.position_along_axis import (
        _per_stim_components, _extract_positions, _bin_axis, _plot_figure,
    )

    pref_proj_full = np.asarray(result.axis_projections, dtype=np.float64)
    orth_proj_full = (
        np.asarray(result.all_orthogonal_projections, dtype=np.float64)
        if result.all_orthogonal_projections is not None else None
    )  # (N, n_orth)
    orth_vars = (
        np.asarray(result.all_orthogonal_variances, dtype=np.float64)
        if result.all_orthogonal_variances is not None else None
    )
    full_idx_by_stim = {str(sid): i for i, sid in enumerate(result_stim_ids)}

    top_orth = max(0, int(config.position_top_n_orth))
    orth_top_cols: list[int] = []
    if (
        top_orth > 0 and orth_proj_full is not None and orth_vars is not None
        and orth_proj_full.ndim == 2 and orth_proj_full.shape[1] >= 1
    ):
        order = np.argsort(-orth_vars)
        orth_top_cols = [int(j) for j in order[:top_orth]]

    for comp_type, fit in axis_fits_preferred.items():
        if fit.selected_indices is None or not fit.stim_ids:
            print(
                f"  [shape-interp] position-along-axis {comp_type}: "
                f"no selected_indices; skipping."
            )
            continue

        # Subset the full-stim AlexNet projections to the stims this type's
        # selector actually picked components for.
        type_stim_ids = list(fit.stim_ids)
        subset_idx = []
        for sid in type_stim_ids:
            key = str(sid)
            if key not in full_idx_by_stim:
                continue
            subset_idx.append(full_idx_by_stim[key])
        subset_idx_arr = np.asarray(subset_idx, dtype=int)
        if subset_idx_arr.size == 0:
            print(
                f"  [shape-interp] position-along-axis {comp_type}: "
                f"no stim_ids in result mapping; skipping."
            )
            continue

        # Reorder selected_indices to match subset_idx_arr (i.e. the order
        # of full result_stim_ids).
        pref_proj = pref_proj_full[subset_idx_arr]
        sid_to_sel = {str(sid): int(idx) for sid, idx in zip(type_stim_ids, fit.selected_indices)}
        ordered_stim_ids = [result_stim_ids[i] for i in subset_idx_arr]
        ordered_sel = [sid_to_sel[str(sid)] for sid in ordered_stim_ids]

        components_by_stim = _per_stim_components(df_for_stims, comp_type)
        pos = _extract_positions(ordered_stim_ids, ordered_sel, components_by_stim)
        if not pos.valid_mask.any():
            print(
                f"  [shape-interp] position-along-axis {comp_type}: "
                f"no extractable positions; skipping."
            )
            continue

        rows = [
            _bin_axis(
                pref_proj, pos, label="preferred (AlexNet)",
                n_bins=config.position_n_bins, z_range=config.position_z_range,
            )
        ]
        if orth_top_cols and orth_proj_full is not None:
            for rank, j in enumerate(orth_top_cols):
                rows.append(
                    _bin_axis(
                        orth_proj_full[subset_idx_arr, j],
                        pos,
                        label=f"orth_{rank + 1} (AlexNet)",
                        n_bins=config.position_n_bins,
                        z_range=config.position_z_range,
                        axis_variance=float(orth_vars[j]) if orth_vars is not None else None,
                    )
                )

        title = (
            f"{title_prefix}  {comp_type} object-centered position along AlexNet axes"
            if title_prefix else
            f"{comp_type} object-centered position along AlexNet axes"
        )
        try:
            fig = _plot_figure(rows, title=title, mu_decoded=fit.prototype_mu_decoded)
        except TypeError:
            # _bin_axis returns a BinnedAxis dataclass that may have a
            # legacy "mag_mean" attribute on older checkouts; surface the
            # error rather than silently swallow.
            raise

        if save_dir is not None:
            os.makedirs(save_dir, exist_ok=True)
            fig_path = os.path.join(
                save_dir, f"{save_prefix}_position_{comp_type}.png"
            )
            fig.savefig(fig_path, dpi=150, bbox_inches="tight")
            print(f"  [shape-interp] saved: {fig_path}")
        if show_plots:
            plt.show()
        else:
            plt.close(fig)


# ---------------------------------------------------------------------------
# Comprehensive summary plot (4 panels)
# ---------------------------------------------------------------------------

def _plot_pc_summary(
    out: ShapeInterpretationResult,
    *,
    title_prefix: str = "",
) -> Optional[plt.Figure]:
    """
    One figure summarizing the AlexNet axis + shape interpretation:

      A: PCA scree (explained variance ratio per PC + cumulative line).
      B: Axis "energy per PC" — bars of w_i² for the preferred axis +
         lines for the kept top orth axes. Tells you how many PCs the
         preferred axis actually cares about.
      C: PC × shape predictability heatmap (rows = component types, cols
         = top-N PCs, cell = CV R² of shape→PC ridge).
      D: Axis × shape predictability bars (preferred + each kept orth
         axis, height = joint shape-S+T+J CV R² with marginal stacks).
    """
    has_scree = out.pca_explained_variance is not None
    has_axis_energy = out.preferred_axis_pc_weights is not None
    has_pc_heatmap = bool(out.pc_fits)
    has_axis_bars = bool(out.variance_partitions)
    n_panels = sum([has_scree, has_axis_energy, has_pc_heatmap, has_axis_bars])
    if n_panels == 0:
        return None

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    axA, axB = axes[0, 0], axes[0, 1]
    axC, axD = axes[1, 0], axes[1, 1]

    # ----- Panel A: scree ------------------------------------------------
    if has_scree:
        ev = np.asarray(out.pca_explained_variance, dtype=np.float64)
        xs = np.arange(1, ev.size + 1)
        axA.bar(xs, ev, color="#3a7bd5", alpha=0.8, label="per-PC")
        ax2 = axA.twinx()
        ax2.plot(xs, np.cumsum(ev), "o-", color="#d54848",
                 markersize=3, linewidth=1.2, label="cumulative")
        ax2.set_ylabel("cumulative variance", color="#d54848", fontsize=9)
        ax2.tick_params(axis="y", labelsize=8, colors="#d54848")
        ax2.set_ylim(0, 1.05)
        axA.set_xlabel("PC index", fontsize=9)
        axA.set_ylabel("variance ratio", color="#3a7bd5", fontsize=9)
        axA.tick_params(axis="both", labelsize=8)
        axA.tick_params(axis="y", colors="#3a7bd5")
        axA.set_title(
            f"A. AlexNet PCA scree  (k={ev.size}, "
            f"cum@all={ev.sum():.1%})",
            fontsize=10,
        )
    else:
        axA.set_visible(False)

    # ----- Panel B: axis energy per PC ----------------------------------
    if has_axis_energy:
        w_pref = np.asarray(out.preferred_axis_pc_weights, dtype=np.float64)
        w2 = w_pref ** 2
        norm = w2.sum()
        frac = w2 / norm if norm > 0 else w2
        xs = np.arange(1, w2.size + 1)
        axB.bar(xs, frac, color="#3a7bd5", alpha=0.85,
                label="preferred")
        if (out.orth_axes_pc_weights is not None
                and out.orth_axes_pc_variances is not None):
            orth = np.asarray(out.orth_axes_pc_weights, dtype=np.float64)
            if orth.ndim == 2 and orth.shape[0] == w_pref.size:
                orth_vars = np.asarray(out.orth_axes_pc_variances, dtype=np.float64)
                order = np.argsort(-orth_vars)
                top_k = min(3, orth.shape[1])
                cmap = plt.cm.viridis(np.linspace(0.2, 0.85, top_k))
                for rank in range(top_k):
                    j = int(order[rank])
                    o2 = orth[:, j] ** 2
                    onorm = o2.sum()
                    of = o2 / onorm if onorm > 0 else o2
                    axB.plot(xs, of, "o-", color=cmap[rank],
                             markersize=3, linewidth=1.0,
                             label=f"orth {rank + 1}")
        axB.set_xlabel("PC index", fontsize=9)
        axB.set_ylabel("|axis_i|² / ||axis||²", fontsize=9)
        axB.set_title(
            "B. Axis energy per PC  (how many PCs the axis cares about)",
            fontsize=10,
        )
        axB.tick_params(axis="both", labelsize=8)
        axB.axhline(0, color="k", lw=0.5)
        axB.legend(fontsize=8, loc="upper right")
    else:
        axB.set_visible(False)

    # ----- Panel C: PC × shape predictability heatmap -------------------
    if has_pc_heatmap:
        pc_names = sorted(
            out.pc_fits.keys(),
            key=lambda s: int(s.split("_")[-1]) if s.split("_")[-1].isdigit() else 0,
        )
        types_in_any = []
        for pc in pc_names:
            for t in out.pc_fits[pc].keys():
                if t not in types_in_any:
                    types_in_any.append(t)
        M = np.full((len(types_in_any), len(pc_names)), np.nan, dtype=np.float64)
        for j, pc in enumerate(pc_names):
            for i, t in enumerate(types_in_any):
                fit = out.pc_fits[pc].get(t)
                if fit is None:
                    continue
                cv = fit.cv_r2_mean
                M[i, j] = cv if cv == cv else np.nan  # nan-safe
        # Clip negative CV R² to 0 for the color scale so the heatmap
        # focuses on positive predictability; annotate raw values.
        vmin, vmax = 0.0, max(0.1, float(np.nanmax(M)) if np.isfinite(np.nanmax(M)) else 0.1)
        im = axC.imshow(np.clip(M, vmin, vmax), aspect="auto",
                        cmap="viridis", vmin=vmin, vmax=vmax)
        axC.set_xticks(np.arange(len(pc_names)))
        axC.set_xticklabels(pc_names, fontsize=8, rotation=45, ha="right")
        axC.set_yticks(np.arange(len(types_in_any)))
        axC.set_yticklabels(types_in_any, fontsize=8)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                v = M[i, j]
                if not np.isnan(v):
                    txt_color = "white" if v < (vmin + vmax) * 0.5 else "black"
                    axC.text(j, i, f"{v:+.2f}", ha="center", va="center",
                             fontsize=7, color=txt_color)
        cbar = plt.colorbar(im, ax=axC, fraction=0.04, pad=0.02)
        cbar.ax.tick_params(labelsize=7)
        axC.set_title(
            "C. shape → PC CV R²  "
            "(how predictable each PC is from shape parameters)",
            fontsize=10,
        )
    else:
        axC.set_visible(False)

    # ----- Panel D: axis × shape predictability bars --------------------
    if has_axis_bars:
        axis_names = list(out.variance_partitions.keys())
        types_order = list(
            out.config.get("component_types",
                           ["Shaft", "Termination", "Junction"])
        )
        # Stack: marginal R² per type, plus a black bar for the joint
        # (S+T+J) on top so you can see both per-type contribution and
        # the joint ceiling.
        x = np.arange(len(axis_names))
        bottoms = np.zeros(len(axis_names))
        cmap = {"Shaft": "#3a7bd5", "Termination": "#3ad58b",
                "Junction": "#d57b3a"}
        for t in types_order:
            heights = []
            for an in axis_names:
                vp = out.variance_partitions[an]
                v = vp.marginal_r2.get(t, float("nan"))
                heights.append(0.0 if v != v else max(0.0, v))
            heights = np.asarray(heights)
            axD.bar(x, heights, bottom=bottoms,
                    color=cmap.get(t, "#888"), label=f"{t} (marg.)",
                    alpha=0.7, width=0.55)
            bottoms = bottoms + heights
        # Joint R² as a black outline marker above the stacked bars.
        joint_vals = []
        for an in axis_names:
            vp = out.variance_partitions[an]
            joint_key = "+".join(types_order)
            v = vp.joint_r2.get(joint_key)
            if v is None and vp.commonality is not None:
                v = vp.commonality.get("_total_R2_STJ")
            joint_vals.append(float("nan") if v is None else float(v))
        joint_arr = np.asarray(joint_vals)
        for xi, jv in zip(x, joint_arr):
            if not np.isnan(jv):
                axD.scatter([xi], [jv], marker="_", s=350, color="black",
                            linewidths=2.5, zorder=10)
        axD.set_xticks(x)
        axD.set_xticklabels(axis_names, fontsize=8, rotation=20, ha="right")
        axD.set_ylabel("CV R² (shape → axis)", fontsize=9)
        axD.tick_params(axis="both", labelsize=8)
        axD.axhline(0, color="k", lw=0.5)
        axD.legend(fontsize=7, loc="upper right",
                   title="bars: per-type marginal\nbar  : joint S+T+J",
                   title_fontsize=7)
        axD.set_title(
            "D. Shape → AlexNet axis CV R²  "
            "(how well shape predicts each axis)",
            fontsize=10,
        )
    else:
        axD.set_visible(False)

    title = (
        f"{title_prefix}  AlexNet axes + shape interpretation summary"
        if title_prefix else
        "AlexNet axes + shape interpretation summary"
    )
    fig.suptitle(title, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


# ---------------------------------------------------------------------------
# Standalone driver: run interpretation from a saved AxisCodingResult JSON
# ---------------------------------------------------------------------------

def load_axis_coding_result(path: str) -> AxisCodingResult:
    """
    Reconstruct an AxisCodingResult from the JSON dumped by
    ``fit_axis_coding``. Unknown keys (forward / backward schema drift) are
    silently ignored so the loader is resilient across versions.
    """
    with open(path) as f:
        d = json.load(f)
    valid = {f.name for f in dataclasses.fields(AxisCodingResult)}
    return AxisCodingResult(**{k: v for k, v in d.items() if k in valid})


def run_interpretation_from_saved(
    result_json_path: str,
    *,
    df: Optional[pd.DataFrame] = None,
    session_id: Optional[str] = None,
    config: Optional[ShapeInterpretationConfig] = None,
    encoders: Optional[dict[str, ComponentEncoder]] = None,
    save_dir: Optional[str] = None,
    save_prefix: Optional[str] = None,
    title_prefix: str = "",
    show_plots: bool = True,
    apply_axis_coding_cleaning: bool = True,
) -> ShapeInterpretationResult:
    """
    Run shape-space interpretation on a previously-saved AxisCodingResult
    JSON, without re-running AlexNet.

    Parameters
    ----------
    result_json_path
        Path to the JSON written by ``fit_axis_coding`` (typically
        ``<save_path>/alexnet_axis_coding/axis_coding_<channel>_AlexNetConv3_<strategy>.json``).
    df
        Pre-loaded compiled dataframe. If ``None``, loaded via
        ``import_from_repository`` using ``session_id`` (or the current
        ``context.ga_database`` if ``session_id`` is also ``None``).
    save_dir
        Where to write figures + JSON. Defaults to the directory of
        ``result_json_path`` — so re-running interpretation drops its output
        alongside the original AlexNet results.
    save_prefix
        Prefix for the interpretation JSON + figure filenames. Defaults to a
        prefix derived from the result-JSON filename so reruns don't
        clobber the original axis-coding dump.
    apply_axis_coding_cleaning
        When ``True`` (default), apply the same trial filters and
        spherical-angle conditioning that ``AxisCodingAnalysis._prepare_dataframe``
        uses, so per-stim component lookups match the saved result. Set
        ``False`` only if ``df`` is already cleaned.
    """
    # Resolve df.
    if df is None:
        from src.repository.import_from_repository import import_from_repository
        if session_id is None:
            from src.repository.export_to_repository import (
                read_session_id_and_date_from_db_name,
            )
            from src.startup import context
            session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
        print(f"[shape-interp] loading compiled df for session {session_id}")
        df = import_from_repository(session_id, "ga", "GAStimInfo", None)
    if apply_axis_coding_cleaning:
        from src.analysis.ga.axis_coding.axis_coding_analysis import (
            AxisCodingAnalysis,
        )
        df = AxisCodingAnalysis._prepare_dataframe(df)

    # Load result.
    result = load_axis_coding_result(result_json_path)
    print(
        f"[shape-interp] loaded result from {result_json_path} "
        f"(n_stim={result.n_stim}, type={result.component_type}, "
        f"strategy={result.strategy_label})"
    )

    # Default save_dir = directory of the result json.
    if save_dir is None:
        save_dir = os.path.dirname(os.path.abspath(result_json_path)) or "."
    if save_prefix is None:
        base = os.path.splitext(os.path.basename(result_json_path))[0]
        save_prefix = f"shape_interp__{base}"

    return interpret_alexnet_axes_with_shape(
        result=result,
        df=df,
        config=config,
        encoders=encoders,
        save_dir=save_dir,
        save_prefix=save_prefix,
        title_prefix=title_prefix or (
            f"{result.component_type} | {result.strategy_label}"
        ),
        show_plots=show_plots,
    )


def find_saved_alexnet_results(roots: Optional[list[str]] = None) -> list[str]:
    """
    Search common plots roots for AlexNet axis-coding result JSONs.

    Defaults to ``/home/connorlab/Documents/plots`` (the project's
    ``Analysis.parse_data_type`` default) plus, if available,
    ``context.ga_plots_dir``.
    """
    import glob
    if roots is None:
        roots = ["/home/connorlab/Documents/plots"]
        try:
            from src.startup import context
            extra = getattr(context, "ga_plots_dir", None)
            if extra:
                roots.append(extra)
        except Exception:
            pass
    seen: list[str] = []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        pattern = os.path.join(
            root, "**", "alexnet_axis_coding",
            "axis_coding_*_AlexNetConv3_*.json",
        )
        for path in glob.glob(pattern, recursive=True):
            if path not in seen:
                seen.append(path)
    return sorted(seen)


def main():
    """
    Re-run interpretation for the current session's AlexNet axis-coding
    result without re-running the AlexNet forward passes.

    Globs the project's plots roots for
    ``axis_coding_*_AlexNetConv3_*.json``. If multiple matches exist, runs
    interpretation on every one of them. For per-file control, call
    ``run_interpretation_from_saved(path)`` directly.
    """
    matches = find_saved_alexnet_results()
    if not matches:
        raise FileNotFoundError(
            "No AlexNet axis-coding result JSONs found under the standard "
            "plots roots. Run alexnet_axis_coding_analysis.main() to "
            "generate one, or pass result_json_path to "
            "run_interpretation_from_saved() directly."
        )
    print(f"[shape-interp] found {len(matches)} result(s):")
    for m in matches:
        print(f"  - {m}")
    for path in matches:
        print(f"\n========== {path} ==========")
        run_interpretation_from_saved(path)


if __name__ == "__main__":
    main()

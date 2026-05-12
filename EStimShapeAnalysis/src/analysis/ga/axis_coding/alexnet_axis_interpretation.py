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
    show_plots: bool = False,
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
    result_stim_ids = list(result.stim_ids)

    # Build a quick stim-grouped df once; we re-use it for each (axis, type).
    df_for_stims = df[df["StimSpecId"].isin(result_stim_ids)].copy()

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

    out = ShapeInterpretationResult(
        config=dataclasses.asdict(config),
        primary_axis_name="preferred",
        axis_fits=axis_fits,
        variance_partitions=variance_partitions,
    )

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
    proj_by_stim = dict(zip(stim_ids, axis_projections.tolist()))

    df_local = df.copy()
    df_local[component_type] = df_local[component_type].apply(_coerce_to_list_of_dicts)
    per_stim_components = df_local.groupby("StimSpecId")[component_type].first()

    kept_stim_ids: list = []
    kept_components: list[list[dict]] = []
    kept_responses: list[float] = []
    for sid in stim_ids:
        if sid not in per_stim_components.index:
            continue
        comps = per_stim_components.loc[sid]
        if comps is None or (isinstance(comps, list) and len(comps) == 0):
            continue
        kept_stim_ids.append(sid)
        kept_components.append(comps)
        kept_responses.append(float(proj_by_stim[sid]))

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
        return None

    types = [t for t in config.component_types if t in per_type]
    n_types = len(types)
    if n_types == 0:
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
    }

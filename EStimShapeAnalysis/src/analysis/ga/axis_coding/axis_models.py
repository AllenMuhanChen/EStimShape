"""
Pluggable models for axis-coding analysis.

A ``ModelSpec`` describes one design matrix to fit a ridge against and run
the axis-coding analysis on (preferred axis = ridge w; orthogonal basis on
the residual subspace; back-projected loadings for the heatmap). Adding a
new model = writing a builder callable that returns a ``BuildResult``.

Built-ins: ``shape_model``, ``appearance_model``, ``shape_plus_appearance_model``.
The default list ``default_axis_models()`` runs all three so each call to
``fit_axis_coding`` produces three figures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from src.analysis.ga.axis_coding.component_encoding import PCAPreprocessor


# ---------------------------------------------------------------------------
# Builder context + output
# ---------------------------------------------------------------------------

@dataclass
class FitContext:
    """
    Inputs available to every model builder. Builders are pure: they read
    these fields and return a ``BuildResult``; they don't fit anything.

    ``X_shape`` is the selector's per-stimulus shape representation (PC space
    if PCA was active, original z-scored feature space otherwise).
    ``A_appearance`` is per-stimulus texture one-hot + average RGB. May be a
    (n_stim, 0) array if appearance columns are missing — builders that need
    it should check first.
    """

    X_shape: np.ndarray
    A_appearance: np.ndarray
    shape_feature_names_model: list[str]   # PC names if PCA, else original
    shape_feature_names_orig: list[str]    # always original feature names
    appearance_feature_names: list[str]
    pca_pre: Optional[PCAPreprocessor]
    responses: np.ndarray


@dataclass
class BuildResult:
    """
    What a model builder returns.

    ``design`` is the matrix the ridge fits. ``feature_names_model`` names
    its columns (e.g. PC1, PC2, ..., texture::SHADE). ``feature_names_interp``
    names columns of the back-projected weight vector — original feature
    names + appearance names — so the loadings heatmap is interpretable.

    ``back_project`` maps a vector in design space (length d_model) to a
    vector in interpretable space (length d_interp). None when the design
    matrix is already in the interpretable space (no PCA, etc.).
    """

    design: np.ndarray
    feature_names_model: list[str]
    feature_names_interp: list[str]
    back_project: Optional[Callable[[np.ndarray], np.ndarray]] = None


@dataclass
class ModelSpec:
    """
    A named axis-coding model. ``builder`` constructs the design matrix
    and back-projection given a ``FitContext``. ``has_shape_mu`` controls
    whether the consolidated plot draws μ panels (the selector's chosen
    shape prototype): True for shape-based models, False for appearance-only.
    """

    name: str
    builder: Callable[[FitContext], BuildResult]
    has_shape_mu: bool = True
    requires_appearance: bool = False


# ---------------------------------------------------------------------------
# Per-model output, populated by the analysis after the ridge is fit.
# ---------------------------------------------------------------------------

@dataclass
class ModelAxisFit:
    """
    Everything the consolidated plot needs to render axis-coding panels for
    one model. All axis fields live in design space; back-projected versions
    live in interpretable feature space (length matches feature_names_interp).
    """

    name: str
    feature_names_model: list[str]
    feature_names_interp: list[str]
    has_shape_mu: bool
    ridge_summary: dict
    predictions: list[float]
    axis_projections: list[float]
    orth_projections: list[float]
    all_orth_projections: list[list[float]]
    orth_axis: list[float]
    all_orth_axes: list[list[float]]
    all_orth_variances: list[float]
    w_in_feature_space: Optional[list[float]] = None
    orth_axis_in_feature_space: Optional[list[float]] = None
    all_orth_axes_in_feature_space: Optional[list[list[float]]] = None
    # ---- Tsao Fig. 4A-style orthogonal-tuning summary --------------------
    # Average tuning curve along (n_axes_used) random axes orthogonal to the
    # preferred axis, on a common z-scored x-grid; plus a Gaussian fit
    # ``a·exp(-x²/σ²) + c`` to that average. The headline scalar
    # ``orth_amplitude_norm = a / (a + c)`` is the fraction of the orthogonal
    # tuning curve that's "bump" vs "baseline": ~0 under axis coding, large
    # under exemplar coding.
    orth_tuning_x: Optional[list[float]] = None        # length n_bins
    orth_tuning_mean: Optional[list[float]] = None     # length n_bins (averaged across axes)
    orth_tuning_sd: Optional[list[float]] = None       # SD across axes per bin
    orth_tuning_count: Optional[list[float]] = None    # mean stim count per bin per axis
    orth_tuning_z_range: Optional[float] = None        # +/- bin edge in z-units
    orth_tuning_fit_z_range: Optional[float] = None    # range used for Gaussian fit
    orth_tuning_n_axes_drawn: Optional[int] = None
    orth_tuning_n_axes_used: Optional[int] = None
    orth_gauss_a: Optional[float] = None
    orth_gauss_sigma: Optional[float] = None
    orth_gauss_c: Optional[float] = None
    orth_amplitude_norm: Optional[float] = None        # a / (a + c)
    orth_gauss_fit_ok: bool = False


# ---------------------------------------------------------------------------
# Built-in models
# ---------------------------------------------------------------------------

def shape_model() -> ModelSpec:
    """Selector-output shape features. PCA-aware: back-projects when active."""
    def build(ctx: FitContext) -> BuildResult:
        if ctx.pca_pre is not None:
            bp = ctx.pca_pre.back_project
            feat_interp = list(ctx.shape_feature_names_orig)
        else:
            bp = None
            feat_interp = list(ctx.shape_feature_names_model)
        return BuildResult(
            design=ctx.X_shape,
            feature_names_model=list(ctx.shape_feature_names_model),
            feature_names_interp=feat_interp,
            back_project=bp,
        )
    return ModelSpec(name="shape", builder=build, has_shape_mu=True)


def appearance_model() -> ModelSpec:
    """Texture one-hot + avg RGB only. No back-projection (already interpretable)."""
    def build(ctx: FitContext) -> BuildResult:
        return BuildResult(
            design=ctx.A_appearance,
            feature_names_model=list(ctx.appearance_feature_names),
            feature_names_interp=list(ctx.appearance_feature_names),
            back_project=None,
        )
    return ModelSpec(
        name="appearance", builder=build,
        has_shape_mu=False, requires_appearance=True,
    )


def shape_plus_appearance_model() -> ModelSpec:
    """
    Joint additive model: [shape | appearance]. Back-projects the shape
    block through PCA (when active) and concatenates appearance unchanged
    so the loadings heatmap rows are original-feature shape + appearance.
    """
    def build(ctx: FitContext) -> BuildResult:
        n_shape = ctx.X_shape.shape[1]
        design = np.column_stack([ctx.X_shape, ctx.A_appearance])
        feat_model = list(ctx.shape_feature_names_model) + list(ctx.appearance_feature_names)
        if ctx.pca_pre is not None:
            feat_interp = list(ctx.shape_feature_names_orig) + list(ctx.appearance_feature_names)
            pca = ctx.pca_pre
            def bp(v: np.ndarray) -> np.ndarray:
                return np.concatenate([pca.back_project(v[:n_shape]), v[n_shape:]])
        else:
            feat_interp = feat_model
            bp = None
        return BuildResult(
            design=design,
            feature_names_model=feat_model,
            feature_names_interp=feat_interp,
            back_project=bp,
        )
    return ModelSpec(
        name="shape+appearance", builder=build,
        has_shape_mu=True, requires_appearance=True,
    )


def default_axis_models() -> list[ModelSpec]:
    """Default model set: shape only, appearance only, additive joint."""
    return [shape_model(), appearance_model(), shape_plus_appearance_model()]

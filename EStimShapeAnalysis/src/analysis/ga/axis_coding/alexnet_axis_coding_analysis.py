"""
AlexNet-feature variant of axis_coding_analysis.

Same orchestration, plotting, μ decoding, ridge fitting, PCA, orth-axis
machinery as ``axis_coding_analysis`` — only the *feature representation*
swaps out. Instead of parameterizing each stimulus by its shape components
(Shaft / Termination / Junction parameter vectors), each stimulus is rendered
through AlexNet conv3 and represented as the flattened activation vector of
that layer. PCA on those activations + ridge regression of neural responses
follows Chang & Tsao (2017) / "A map of object space in primate IT".

Architecture (mirrors axis_coding_analysis):

  AlexNetActivationExtractor
      Loads the ONNX AlexNet (conv3 head) and runs ShapePreprocessTransform on
      each image. Caches per-path so repeated stim_ids hit the model once.

  AlexNetFeatureEncoder
      Quacks like ComponentEncoder: feature_names / fit_scaler /
      transform_with_scaler / inverse_scale / decode_to_parameters. Holds no
      shape-parameter schema; just z-scores raw activation vectors.

  AlexNetAxisCodingDataset.build(...)
      Builds an AxisCodingDataset whose components_per_stim is a list of
      shape (1, D) arrays — exactly one "component" per stimulus, namely its
      conv3 activation vector. The downstream pipeline (selector, PCA,
      ridge, plotting) treats this like any other (m_i, d) dataset.

  SingleComponentSelector
      Trivial selector for the m_i = 1 case: returns the only component per
      stimulus and reports μ as the response-weighted mean (in
      selector-space, i.e. PC space if PCA was used else feature space).

  AlexNetAxisCodingAnalysis(AxisCodingAnalysis)
      Subclass with component_types=["AlexNetConv3"]. Overrides only the two
      hook methods (_build_encoders_for_run + _fit_one_strategy) and the
      save_subdir constant. Everything else — analyze() body, console output,
      figure layout, JSON export, repository upsert — is inherited.

This module is runnable side-by-side with axis_coding_analysis.main() since
its results land in a separate save_subdir and use a different component_type
string in the repository.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, Union

import numpy as np
import onnxruntime
import pandas as pd
from PIL import Image
from sklearn.preprocessing import StandardScaler

from src.analysis.ga.axis_coding.axis_coding_analysis import (
    AxisCodingAnalysis,
    AxisCodingResult,
    AxisCodingStrategy,
    default_ridge_factory,
    fit_axis_coding,
)
from src.analysis.ga.axis_coding.axis_models import alexnet_model
from src.analysis.ga.axis_coding.axis_coding_dataset import (
    AxisCodingDataset,
    _extract_per_trial_response,
)
from src.analysis.ga.axis_coding.component_encoding import ComponentEncoder
from src.analysis.ga.axis_coding.component_selectors import ComponentSelector
from src.analysis.ga.receptive_field_filter import ReceptiveFieldFilter
from src.pga.mock.exp_to_alexnet_transform import ShapePreprocessTransform
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context


# ---------------------------------------------------------------------------
# AlexNet activation extraction
# ---------------------------------------------------------------------------

# Default ONNX model path matches the one used by AlexNetONNXResponseParser
# and alexnet_ga_responses.extract_activations.
DEFAULT_ONNX_PATH = (
    "/home/connorlab/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3"
)
DEFAULT_LAYER_OUTPUT_NAME = "conv3"


class AlexNetActivationExtractor:
    """
    Run images through AlexNet (ONNX) and return a per-stim activation vector
    from a chosen layer. Caches per-image-path so repeated stim_ids only incur
    one forward pass.

    Spatial handling for conv layers (``pooling``):
      - ``"mean_pool"`` (default): average activations over the H×W grid so
        each filter contributes one number per stim. Translation-invariant,
        D = C. Closest to Chang & Tsao 2017 (PCA on per-stim feature vectors).
      - ``"max_pool"``: max over H×W. "Is this filter active anywhere?"
      - ``"center"``: take a single (x, y) location (default mid-grid). D = C.
        Matches the project's existing single-unit convention
        (``conv3_u374_x7_y7`` in alexnet_context.py).
      - ``"flatten"``: full C × H × W with no pooling. Use only if you want
        spatial position baked into the feature representation. Note that
        conv weights are tied across the grid, so neighbouring spatial
        locations carry redundant information.

    The default preprocessing is ShapePreprocessTransform (227×227, bbox-crop
    on gray background) — same transform used by the mock-GA AlexNet pipeline,
    so axis-coding results are directly comparable to those response signals.
    """

    POOLING_OPTIONS = ("mean_pool", "max_pool", "center", "flatten")

    def __init__(
        self,
        onnx_path: str = DEFAULT_ONNX_PATH,
        layer_output_name: str = DEFAULT_LAYER_OUTPUT_NAME,
        bbox_scale: float = 0.5,
        target_size: int = 227,
        background_value: int = 127,
        pooling: str = "max_pool",
        center_xy: Optional[tuple[int, int]] = None,
    ):
        if pooling not in self.POOLING_OPTIONS:
            raise ValueError(
                f"pooling={pooling!r} must be one of {self.POOLING_OPTIONS}"
            )
        self.onnx_path = onnx_path
        self.layer_output_name = layer_output_name
        self.pooling = pooling
        self.center_xy = center_xy  # None → mid-grid resolved on first call
        self._session: Optional[onnxruntime.InferenceSession] = None
        self._input_name: Optional[str] = None
        self._activation_shape: Optional[tuple[int, ...]] = None
        self.transform = ShapePreprocessTransform(
            target_size=target_size,
            bbox_scale=bbox_scale,
            background_value=background_value,
        )
        self._cache: dict[str, np.ndarray] = {}

    def _ensure_session(self) -> onnxruntime.InferenceSession:
        if self._session is None:
            self._session = onnxruntime.InferenceSession(self.onnx_path)
            self._input_name = self._session.get_inputs()[0].name
        return self._session

    @property
    def activation_shape(self) -> tuple[int, ...]:
        """Raw conv output shape excluding the batch dim (C, H, W)."""
        if self._activation_shape is None:
            raise RuntimeError(
                "activation_shape unknown until at least one image has been "
                "extracted. Call extract() first."
            )
        return self._activation_shape

    def _pool(self, raw: np.ndarray) -> np.ndarray:
        """Apply the configured pooling to a (C, H, W) array → (D,) vector."""
        if self.pooling == "flatten":
            return raw.ravel()
        if self.pooling == "mean_pool":
            return raw.mean(axis=(1, 2))
        if self.pooling == "max_pool":
            return raw.max(axis=(1, 2))
        if self.pooling == "center":
            _, h, w = raw.shape
            x, y = self.center_xy if self.center_xy is not None else (h // 2, w // 2)
            return raw[:, x, y]
        raise AssertionError(f"unreachable pooling={self.pooling}")  # pragma: no cover

    def extract(self, image_path: str) -> np.ndarray:
        """Return the pooled (D,) activation vector for an image."""
        if image_path in self._cache:
            return self._cache[image_path]

        session = self._ensure_session()
        image = Image.open(image_path).convert("RGB")
        tensor = self.transform(image).unsqueeze(0).numpy()
        out = session.run(
            [self.layer_output_name],
            {self._input_name: tensor},
        )[0]  # shape (1, C, H, W)

        if self._activation_shape is None:
            self._activation_shape = tuple(out.shape[1:])

        raw = np.asarray(out[0], dtype=np.float64)
        pooled = self._pool(raw)
        self._cache[image_path] = pooled
        return pooled

    def extract_many(self, paths: list[str]) -> list[np.ndarray]:
        return [self.extract(p) for p in paths]

    def feature_names(self) -> list[str]:
        """One label per pooled feature; depends on ``pooling``."""
        c, h, w = self.activation_shape  # type: ignore[misc]
        layer = self.layer_output_name
        if self.pooling == "flatten":
            return [f"{layer}_u{u}_x{x}_y{y}"
                    for u in range(c) for x in range(h) for y in range(w)]
        if self.pooling == "mean_pool":
            return [f"{layer}_u{u}_meanpool" for u in range(c)]
        if self.pooling == "max_pool":
            return [f"{layer}_u{u}_maxpool" for u in range(c)]
        if self.pooling == "center":
            x, y = self.center_xy if self.center_xy is not None else (h // 2, w // 2)
            return [f"{layer}_u{u}_x{x}_y{y}" for u in range(c)]
        raise AssertionError(f"unreachable pooling={self.pooling}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Encoder shim — quacks like ComponentEncoder but for raw activation vectors
# ---------------------------------------------------------------------------

@dataclass
class AlexNetFeatureEncoder:
    """
    Minimal ComponentEncoder-compatible shim for AlexNet activations.

    Holds the StandardScaler and the feature names. Implements the surface
    that ``fit_axis_coding`` touches on encoders: ``feature_names``,
    ``n_features``, ``encode_components``, ``fit_scaler``,
    ``transform_with_scaler``, ``inverse_scale``, ``decode_to_parameters``.

    ``encode_components`` is a no-op pass-through here because per-stim
    components are *already* the encoded activation vectors (one per stim) —
    they don't need encoding from a dict the way shape components do.

    ``decode_to_parameters`` returns a ``{feature_name: value}`` dict so
    plot_mu_decoded has something to display, but there is no continuous
    parameter space to recover the way there is for shape μ.
    """

    feature_names: list[str]
    scaler: Optional[StandardScaler] = None
    # Kept for ComponentEncoder API symmetry (plot code introspects these on
    # the shape encoder); always empty for AlexNet.
    linear_params: list[str] = field(default_factory=list)
    circular_params: list[str] = field(default_factory=list)
    spherical_params: list[str] = field(default_factory=list)

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    def encode_components(self, components: list) -> np.ndarray:
        """
        Pass-through. ``components`` is already a list (or array) of
        already-encoded activation vectors for one stimulus — for AlexNet
        that list is always length 1.
        """
        if components is None or len(components) == 0:
            return np.zeros((0, self.n_features), dtype=np.float64)
        return np.asarray(components, dtype=np.float64)

    def fit_scaler(self, all_components_stacked: np.ndarray) -> None:
        scaler = StandardScaler()
        scaler.fit(all_components_stacked)
        self.scaler = scaler

    def transform_with_scaler(self, encoded: np.ndarray) -> np.ndarray:
        if self.scaler is None:
            raise RuntimeError("Scaler not fit. Call fit_scaler() first.")
        if encoded.shape[0] == 0:
            return encoded
        result = self.scaler.transform(encoded)
        # Zero-variance units (dead conv3 channels in this stimulus set) come
        # back NaN after z-scoring; replace with 0 (= the z-scored mean) so
        # they contribute nothing rather than poisoning ridge/PCA.
        return np.where(np.isfinite(result), result, 0.0)

    def inverse_scale(self, z_scored: np.ndarray) -> np.ndarray:
        if self.scaler is None:
            raise RuntimeError("Scaler not fit. Call fit_scaler() first.")
        v = np.asarray(z_scored, dtype=np.float64).reshape(1, -1)
        return self.scaler.inverse_transform(v)[0]

    def decode_to_parameters(self, encoded_unscaled: np.ndarray) -> dict:
        v = np.asarray(encoded_unscaled, dtype=np.float64).ravel()
        return {name: float(v[i]) for i, name in enumerate(self.feature_names)}


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------

class AlexNetAxisCodingDataset:
    """
    Build an AxisCodingDataset where each stimulus contributes a single
    "component": its AlexNet conv3 activation vector.

    Result shape: ``components_per_stim`` is a list of (1, D) arrays where D
    is the flattened conv3 size. The selector + PCA + ridge stack downstream
    treats this exactly like shape components with m_i = 1.
    """

    @staticmethod
    def build(
        df: pd.DataFrame,
        encoder: AlexNetFeatureEncoder,
        channel: Union[str, list[str]],
        spike_rates_col: Optional[str],
        extractor: AlexNetActivationExtractor,
        stim_path_col: str = "ThumbnailPath",
        component_type_label: str = "AlexNetConv3",
    ) -> AxisCodingDataset:
        df = df.copy()
        df = df[df["StimSpecId"].notna()]

        if stim_path_col not in df.columns:
            raise KeyError(
                f"Column '{stim_path_col}' not in dataframe (needed to locate "
                f"image files for AlexNet). Available: {list(df.columns)}"
            )

        # Per-trial responses (same convention as the shape pipeline).
        df["_alex_resp"] = _extract_per_trial_response(df, channel, spike_rates_col)
        before = len(df)
        df = df[df["_alex_resp"].notna()]
        n_dropped_no_response = before - len(df)

        per_stim_response = df.groupby("StimSpecId")["_alex_resp"].mean()
        per_stim_path = df.groupby("StimSpecId")[stim_path_col].first()

        kept_stim_ids: list = []
        kept_paths: list[str] = []
        kept_responses: list[float] = []
        n_dropped_no_components = 0
        for stim_id, path in per_stim_path.items():
            if path is None or not isinstance(path, str) or not os.path.exists(path):
                n_dropped_no_components += 1
                continue
            kept_stim_ids.append(stim_id)
            kept_paths.append(path)
            kept_responses.append(float(per_stim_response[stim_id]))

        if not kept_stim_ids:
            raise RuntimeError(
                f"No stimuli with a usable {stim_path_col} found for "
                f"AlexNet feature extraction."
            )

        print(
            f"  [alexnet] extracting conv3 for {len(kept_paths)} stimuli "
            f"(channel={channel})"
        )
        activations = extractor.extract_many(kept_paths)
        # All activations share the same flat length.
        D = activations[0].shape[0]

        # Now that the extractor has seen at least one image its (C,H,W) is
        # known; populate encoder feature names if not already done.
        if not encoder.feature_names:
            encoder.feature_names = extractor.feature_names()
        if len(encoder.feature_names) != D:
            raise RuntimeError(
                f"Encoder feature_names length ({len(encoder.feature_names)}) "
                f"does not match extracted activation length ({D})."
            )

        # Encode (already-encoded for AlexNet) then fit the encoder scaler on
        # the union, exactly as AxisCodingDataset.build does for shape.
        encoded_per_stim = [a.reshape(1, D) for a in activations]
        all_components = np.vstack(encoded_per_stim)
        encoder.fit_scaler(all_components)
        scaled_per_stim = [encoder.transform_with_scaler(e) for e in encoded_per_stim]

        return AxisCodingDataset(
            components_per_stim=scaled_per_stim,
            responses=np.asarray(kept_responses, dtype=np.float64),
            stim_ids=np.asarray(kept_stim_ids),
            feature_names=list(encoder.feature_names),
            encoder=encoder,
            n_dropped_no_components=n_dropped_no_components,
            n_dropped_no_response=n_dropped_no_response,
        )


# ---------------------------------------------------------------------------
# Trivial selector for the m_i = 1 case
# ---------------------------------------------------------------------------

class SingleComponentSelector(ComponentSelector):
    """
    Returns the only component per stimulus and reports μ = response-weighted
    mean of those components (in whatever space the selector receives them —
    PC space if PCA was active, z-scored feature space otherwise).

    Used by AlexNet axis coding where each stimulus contributes exactly one
    activation vector and the EM-style μ search in FixedCovariance / Soft-
    Attention selectors would be a no-op. The response-weighted mean still
    gives a meaningful μ for downstream plotting / decoding.
    """

    def __init__(self, response_weight_floor: float = 0.0):
        self.response_weight_floor = float(response_weight_floor)
        self.mu_: Optional[np.ndarray] = None
        self.selected_indices_: Optional[np.ndarray] = None

    def fit(
        self,
        components_per_stim: list[np.ndarray],
        responses: np.ndarray,
    ) -> "SingleComponentSelector":
        if any(c.shape[0] != 1 for c in components_per_stim):
            raise ValueError(
                "SingleComponentSelector expects exactly one component per "
                "stimulus (m_i = 1). Got mixed shapes."
            )
        X = np.vstack([c[0] for c in components_per_stim])  # (N, d)
        w = np.asarray(responses, dtype=np.float64)
        if self.response_weight_floor > 0:
            w = np.where(w > self.response_weight_floor, w, 0.0)
        total = w.sum()
        if total <= 0:
            # Fall back to unweighted mean if responses are all-zero / negative.
            self.mu_ = X.mean(axis=0)
        else:
            self.mu_ = (w[:, None] * X).sum(axis=0) / total
        self.selected_indices_ = np.zeros(len(components_per_stim), dtype=int)
        return self

    def select_indices(self, components_per_stim: list[np.ndarray]) -> np.ndarray:
        return np.zeros(len(components_per_stim), dtype=int)

    def summary(self) -> dict:
        return {
            "name": "SingleComponentSelector",
            "response_weight_floor": self.response_weight_floor,
            "mu": None if self.mu_ is None else self.mu_.tolist(),
        }


# ---------------------------------------------------------------------------
# Strategy + analyzer
# ---------------------------------------------------------------------------

DEFAULT_COMPONENT_TYPE = "AlexNetConv3"


def make_default_alexnet_strategies(n_pcs: int = 50) -> list[AxisCodingStrategy]:
    """
    Default strategy list. Single strategy: trivial selector + PCA + ridge,
    matching the Chang & Tsao recipe (PCA on activations → linear regression
    onto responses).
    """
    return [
        AxisCodingStrategy(
            label=f"alexnet_pca{n_pcs}",
            selector_factory=lambda: SingleComponentSelector(),
            ridge_factory=default_ridge_factory,
            n_pcs=n_pcs,
        ),
    ]


class AlexNetAxisCodingAnalysis(AxisCodingAnalysis):
    """
    AxisCodingAnalysis variant whose features come from AlexNet conv3 rather
    than shape-component parameters. Inherits the full analyze() body and
    only overrides the two hook methods plus the save-subdir constant.

    component_types is forced to a single pseudo-type ("AlexNetConv3") so the
    inherited per-type loop runs once. The extractor is shared across the run
    so caching is effective.
    """

    _save_subdir = "alexnet_axis_coding"
    _primary_model_name = "alexnet"

    def __init__(
        self,
        *,
        extractor: Optional[AlexNetActivationExtractor] = None,
        stim_path_col: str = "ThumbnailPath",
        strategies: Optional[list[AxisCodingStrategy]] = None,
        n_pcs: int = 50,
        run_shape_interpretation: bool = True,
        shape_interpretation_config: Optional["ShapeInterpretationConfig"] = None,
        **kwargs,
    ):
        # Force component_types to the AlexNet pseudo-type and supply matching
        # placeholder encoders that the base __init__ will use to seed
        # self.encoders. Real encoders are created in _build_encoders_for_run.
        kwargs["component_types"] = [DEFAULT_COMPONENT_TYPE]
        kwargs["encoders"] = {DEFAULT_COMPONENT_TYPE: AlexNetFeatureEncoder(feature_names=[])}
        kwargs["strategies"] = strategies or make_default_alexnet_strategies(n_pcs=n_pcs)
        # AlexNet conv3 already mixes shape and color/texture, so a shape-vs-
        # appearance decomposition is uninterpretable here. Use a single
        # primary model named "alexnet" and no appearance/joint comparison.
        kwargs.setdefault("axis_models", [alexnet_model()])
        super().__init__(**kwargs)
        self.extractor = extractor or AlexNetActivationExtractor()
        self.stim_path_col = stim_path_col
        # Opt-in post-fit shape-space interpretation of the AlexNet preferred
        # / orthogonal axes (see alexnet_axis_interpretation.py). Defaults on
        # because the interpretation is cheap relative to the AlexNet forward
        # passes and adds materially to the diagnostic output.
        self.run_shape_interpretation = bool(run_shape_interpretation)
        self.shape_interpretation_config = shape_interpretation_config

    # ------------------------------------------------------------------
    # Hook overrides
    # ------------------------------------------------------------------

    def _build_encoders_for_run(self) -> dict[str, ComponentEncoder]:
        # Fresh encoder per analyze() call so its StandardScaler is fit on
        # this session's activations only. Feature names are populated by the
        # dataset builder once the extractor has seen one image.
        return {DEFAULT_COMPONENT_TYPE: AlexNetFeatureEncoder(feature_names=[])}

    def _fit_one_strategy(
        self,
        *,
        df: pd.DataFrame,
        component_type: str,
        encoder,
        strategy: AxisCodingStrategy,
        channel,
        save_dir: Optional[str],
    ) -> AxisCodingResult:
        dataset = AlexNetAxisCodingDataset.build(
            df=df,
            encoder=encoder,
            channel=channel,
            spike_rates_col=self.spike_rates_col,
            extractor=self.extractor,
            stim_path_col=self.stim_path_col,
            component_type_label=component_type,
        )
        result = fit_axis_coding(
            df=df,
            component_type=component_type,
            encoder=encoder,
            selector=strategy.selector_factory(),
            channel=channel,
            spike_rates_col=self.spike_rates_col,
            strategy_label=strategy.label,
            save_dir=save_dir,
            ridge_factory=strategy.ridge_factory,
            n_pcs=strategy.n_pcs,
            axis_models=self.axis_models,
            dataset=dataset,
            primary_model_name=self._primary_model_name,
        )

        # Opt-in post-fit shape-space interpretation of the AlexNet preferred
        # axis + top-N orthogonal axes. Imported lazily so the heavyweight
        # MultiPrototypeAttentionSelector isn't pulled in when this feature
        # is disabled.
        if self.run_shape_interpretation:
            try:
                from src.analysis.ga.axis_coding.alexnet_axis_interpretation import (
                    interpret_alexnet_axes_with_shape,
                )
                interpret_alexnet_axes_with_shape(
                    result=result,
                    df=df,
                    config=self.shape_interpretation_config,
                    save_dir=save_dir,
                    save_prefix=(
                        f"alexnet_shape_interp_"
                        f"{component_type}_{strategy.label}"
                    ),
                    title_prefix=(
                        f"{component_type} | {strategy.label}"
                    ),
                    show_plots=self.show_plots,
                )
            except Exception as exc:
                import traceback
                print(f"  [shape-interp] FAILED: {exc}")
                traceback.print_exc()
        return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def make_default_alexnet_analyzer_kwargs() -> dict:
    """Mirror of axis_coding_analysis.make_default_analyzer_kwargs."""
    return dict(
        n_pcs=50,
        outlier_sigma=2.0,
        outlier_min_trials=5,
        rf_filter=ReceptiveFieldFilter(plot=True, mahal_cutoff=3.5),
        n_stimuli_per_axis=15,
    )


def main():
    """Single-session entry point. Runs side-by-side with axis_coding_analysis."""
    analysis = AlexNetAxisCodingAnalysis(**make_default_alexnet_analyzer_kwargs())
    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    compiled_data = None
    channel = "Cluster"
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


if __name__ == "__main__":
    main()

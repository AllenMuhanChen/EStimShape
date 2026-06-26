from __future__ import annotations

"""AlexNet conv3 activation embedding for stimuli.

Runs each stimulus image through AlexNet, pulls the layer-3 (conv3) activation,
and reduces the population of stimuli to a low-dimensional PCA embedding. The
first two PCs of this space are a rough proxy for "how geometrically similar two
shapes look to AlexNet," useful to overlay on the neural stimulus-PCA scatter
(see StimulusPCAAnalysis): do stimuli that cluster in V4 response space also
look alike to a generic vision model?

Image preprocessing and ONNX inference are delegated to
``AlexNetActivationExtractor`` from the axis-coding module, which already
applies ``ShapePreprocessTransform`` (bbox-crop, centered on a gray background,
resized to 227×227 — the size the ONNX model expects). Reusing it keeps this
embedding consistent with the axis-coding / mock-GA AlexNet pipeline and avoids
re-solving the input-sizing problem.

The extractor (and its torch / onnxruntime imports) is constructed lazily, so
this module imports cleanly without the deep-learning stack.
"""

from typing import Optional

import os
import numpy as np
from sklearn.decomposition import PCA

# Same default the axis-coding analysis uses.
DEFAULT_ONNX_PATH = (
    "/home/connorlab/git/EStimShape/EStimShapeAnalysis/data/AlexNetONNX_with_conv3"
)


class AlexNetLayer3PCAEmbedder:
    """Embed stimuli into a PCA space of their AlexNet conv3 activations.

    Args:
        onnx_path: Path to the AlexNet ONNX model exposing a ``conv3`` output.
        layer_output_name: Name of the ONNX output to read (default ``conv3``).
        n_components: Number of PCs to keep (default 2).
        pooling: How conv3's (C, H, W) map is reduced to a vector per stimulus
            (``max_pool`` / ``mean_pool`` / ``center`` / ``flatten``). Default
            ``max_pool`` matches the axis-coding default.
        bbox_scale / target_size / background_value: Passed through to
            ``ShapePreprocessTransform`` via the extractor.
    """

    def __init__(self, onnx_path: str = DEFAULT_ONNX_PATH, *,
                 layer_output_name: str = "conv3", n_components: int = 2,
                 pooling: str = "max_pool", bbox_scale: float = 0.5,
                 target_size: int = 227, background_value: int = 127):
        self.onnx_path = onnx_path
        self.layer_output_name = layer_output_name
        self.n_components = n_components
        self.pooling = pooling
        self.bbox_scale = bbox_scale
        self.target_size = target_size
        self.background_value = background_value
        self._extractor = None
        # Populated after embed(): the fitted PCA over AlexNet features.
        self.pca: Optional[PCA] = None

    def _get_extractor(self):
        if self._extractor is None:
            from src.analysis.ga.axis_coding.alexnet_axis_coding_analysis import (
                AlexNetActivationExtractor,
            )
            self._extractor = AlexNetActivationExtractor(
                onnx_path=self.onnx_path,
                layer_output_name=self.layer_output_name,
                bbox_scale=self.bbox_scale,
                target_size=self.target_size,
                background_value=self.background_value,
                pooling=self.pooling,
            )
        return self._extractor

    def embed(self, stim_paths: dict) -> dict:
        """Map ``{stim_id: image_path}`` to ``{stim_id: pc_vector}``.

        Stimuli whose image is missing or unreadable are skipped (left out of
        the returned dict). PCA is fit only on the successfully-loaded images.
        """
        extractor = self._get_extractor()
        ids, features = [], []
        for stim_id, path in stim_paths.items():
            if not path or not os.path.exists(path):
                continue
            try:
                features.append(np.asarray(extractor.extract(path), dtype=float))
                ids.append(stim_id)
            except Exception as exc:
                print(f"AlexNet embedding: failed on {path}: {exc}")

        if len(ids) < 2:
            print(f"AlexNet embedding: only {len(ids)} image(s) loaded; need >=2. Skipping.")
            return {}

        X = np.vstack(features)
        n_components = min(self.n_components, *X.shape)
        self.pca = PCA(n_components=n_components)
        coords = self.pca.fit_transform(X)
        return {stim_id: coords[i] for i, stim_id in enumerate(ids)}

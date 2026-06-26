from __future__ import annotations

"""AlexNet conv3 activation embedding for stimuli.

Runs each stimulus image through AlexNet, pulls the layer-3 (conv3) feature
map, flattens it, and reduces the population of stimuli to a low-dimensional
PCA embedding. The first two PCs of this space are a rough proxy for "how
geometrically similar two shapes look to AlexNet," which is useful to overlay
on the neural stimulus-PCA scatter (see StimulusPCAAnalysis) -- it lets you
ask whether stimuli that cluster in V4 response space also look alike to a
generic vision model.

The ONNX / torch / PIL imports are deferred into the methods that need them so
this module (and anything that consumes the embedding as a precomputed dict)
imports cleanly in environments without the deep-learning stack installed.
"""

from typing import Optional

import numpy as np
from sklearn.decomposition import PCA


class AlexNetLayer3PCAEmbedder:
    """Embed stimuli into a PCA space of their AlexNet conv3 activations.

    Mirrors the preprocessing in ``src.pga.alexnet.onnx_parser`` (PILToTensor,
    no normalization) but keeps the *whole* conv3 feature map rather than a
    single unit.

    Args:
        onnx_path: Path to the AlexNet ONNX model exposing a ``conv3`` output.
        layer_output_name: Name of the ONNX output to read (default ``conv3``).
        n_components: Number of PCs to keep (default 2).
        image_size: Optional (W, H) to resize each image to before inference.
            ``None`` keeps the image as-is (matching the existing parser, which
            assumes stimuli are already the right size).
    """

    def __init__(self, onnx_path: str, *, layer_output_name: str = "conv3",
                 n_components: int = 2, image_size: Optional[tuple[int, int]] = None):
        self.onnx_path = onnx_path
        self.layer_output_name = layer_output_name
        self.n_components = n_components
        self.image_size = image_size
        self._session = None
        # Populated after embed(): the fitted PCA, so callers can inspect the
        # explained variance of the AlexNet feature space too.
        self.pca: Optional[PCA] = None

    def embed(self, stim_paths: dict) -> dict:
        """Map ``{stim_id: image_path}`` to ``{stim_id: pc_vector}``.

        Stimuli whose image is missing or unreadable are skipped (left out of
        the returned dict). PCA is fit only on the successfully-loaded images.
        """
        ids, features = [], []
        for stim_id, path in stim_paths.items():
            vec = self._extract_features(path)
            if vec is not None:
                ids.append(stim_id)
                features.append(vec)

        if len(ids) < 2:
            print(f"AlexNet embedding: only {len(ids)} image(s) loaded; need >=2. Skipping.")
            return {}

        X = np.vstack(features)
        n_components = min(self.n_components, *X.shape)
        self.pca = PCA(n_components=n_components)
        coords = self.pca.fit_transform(X)
        return {stim_id: coords[i] for i, stim_id in enumerate(ids)}

    # ---- ONNX feature extraction (deferred imports) ----------------------
    def _get_session(self):
        if self._session is None:
            import onnxruntime
            self._session = onnxruntime.InferenceSession(self.onnx_path)
        return self._session

    def _extract_features(self, image_path: Optional[str]) -> Optional[np.ndarray]:
        import os
        if not image_path or not os.path.exists(image_path):
            return None
        try:
            from PIL import Image
            import torchvision.transforms as transforms

            transform = transforms.Compose([
                transforms.PILToTensor(),
                lambda x: x * 1.0,
            ])
            image = Image.open(image_path).convert('RGB')
            if self.image_size is not None:
                image = image.resize(self.image_size)
            input_tensor = transform(image).unsqueeze(0)

            session = self._get_session()
            input_name = session.get_inputs()[0].name
            outputs = session.run([self.layer_output_name], {input_name: input_tensor.numpy()})
            # outputs[0] is [1, C, H, W]; flatten the whole conv3 map.
            return np.asarray(outputs[0]).reshape(-1)
        except Exception as exc:
            print(f"AlexNet embedding: failed on {image_path}: {exc}")
            return None

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


@dataclass
class ComponentEncoder:
    """
    Turn a list of component dicts (one stimulus's components for one type) into a
    fixed-width numeric matrix.

    Parameter kinds:
      - ``linear_params``    raw scalar value
      - ``circular_params``  planar angle ∈ [0, 2π); encoded as (cos, sin)
      - ``spherical_params`` base name for a {theta, phi} pair on a sphere;
                             encoded as the 3D unit vector
                             (sin φ cos θ, sin φ sin θ, cos φ).

    Why 3D unit vectors for spherical pairs (rather than independent (cos, sin)
    encodings of θ and φ separately):
      - φ ∈ [0, π] is *not* periodic; its (cos, sin) encoding wraps it as if it
        were, which puts spurious distance between φ and π+φ.
      - At the poles (φ → 0, π), θ is undefined; an independent encoding still
        treats different θ values as distant, which is wrong.
      - The 3D unit vector encoding has Euclidean distance equal to the chord
        distance on the sphere, which is monotonic in geodesic distance and
        correct for any (θ, φ).

    After encoding, call ``fit_scaler`` on the stacked array of every component
    from every stimulus, then ``transform_with_scaler`` on each row, so distances
    across components/stimuli live on the same scale.
    """

    linear_params: list[str]
    circular_params: list[str]
    spherical_params: list[str] = field(default_factory=list)
    scaler: Optional[StandardScaler] = None
    feature_names: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.feature_names:
            self.feature_names = self._build_feature_names()

    @property
    def n_features(self) -> int:
        return (
            len(self.linear_params)
            + 2 * len(self.circular_params)
            + 3 * len(self.spherical_params)
        )

    def _build_feature_names(self) -> list[str]:
        names: list[str] = []
        for p in self.linear_params:
            names.append(p)
        for p in self.circular_params:
            names.append(f"{p}.cos")
            names.append(f"{p}.sin")
        for p in self.spherical_params:
            names.append(f"{p}.x")
            names.append(f"{p}.y")
            names.append(f"{p}.z")
        return names

    def encode_components(self, components: list[dict]) -> np.ndarray:
        """Encode every component of one stimulus into an (m, d) array (un-scaled)."""
        if components is None or len(components) == 0:
            return np.zeros((0, self.n_features), dtype=np.float64)

        rows = []
        for comp in components:
            row = np.empty(self.n_features, dtype=np.float64)
            i = 0
            for p in self.linear_params:
                row[i] = float(_resolve_dotted(comp, p))
                i += 1
            for p in self.circular_params:
                v = float(_resolve_dotted(comp, p))
                row[i] = np.cos(v)
                row[i + 1] = np.sin(v)
                i += 2
            for p in self.spherical_params:
                theta = float(_resolve_dotted(comp, f"{p}.theta"))
                phi = float(_resolve_dotted(comp, f"{p}.phi"))
                sin_phi = np.sin(phi)
                row[i] = sin_phi * np.cos(theta)
                row[i + 1] = sin_phi * np.sin(theta)
                row[i + 2] = np.cos(phi)
                i += 3
            rows.append(row)
        return np.asarray(rows, dtype=np.float64)

    def fit_scaler(self, all_components_stacked: np.ndarray) -> None:
        """Fit the StandardScaler on the union of all components from all stimuli."""
        scaler = StandardScaler()
        scaler.fit(all_components_stacked)
        self.scaler = scaler

    def transform_with_scaler(self, encoded: np.ndarray) -> np.ndarray:
        if self.scaler is None:
            raise RuntimeError("Scaler not fit. Call fit_scaler() first.")
        if encoded.shape[0] == 0:
            return encoded
        result = self.scaler.transform(encoded)
        # Zero-variance features (std=0) produce NaN after scaling.
        # Replace with 0 (= the z-scored mean) so they contribute nothing
        # to distances or regression without crashing downstream code.
        return np.where(np.isfinite(result), result, 0.0)

    def inverse_scale(self, z_scored: np.ndarray) -> np.ndarray:
        """Inverse of ``transform_with_scaler`` for a single feature row."""
        if self.scaler is None:
            raise RuntimeError("Scaler not fit. Call fit_scaler() first.")
        v = np.asarray(z_scored, dtype=np.float64).reshape(1, -1)
        return self.scaler.inverse_transform(v)[0]

    def decode_to_parameters(self, encoded_unscaled: np.ndarray) -> dict:
        """
        Inverse of ``encode_components`` for one (d,) feature vector in the
        original (un-z-scored) feature space.

        Linear params return their raw value.
        Circular (cos, sin) → angle in [-π, π] via atan2 (norm-invariant).
        Spherical (x, y, z) → (theta, phi); the triple is renormalized to the
        unit sphere first since arbitrary linear combinations (PCA back-projection,
        attention pooling, scaler inversion) can leave it off the sphere.
        """
        v = np.asarray(encoded_unscaled, dtype=np.float64).ravel()
        out: dict = {}
        i = 0
        for p in self.linear_params:
            out[p] = float(v[i])
            i += 1
        for p in self.circular_params:
            c = float(v[i])
            s = float(v[i + 1])
            out[p] = float(np.arctan2(s, c))
            i += 2
        for p in self.spherical_params:
            xyz = v[i:i + 3]
            norm = float(np.linalg.norm(xyz))
            if norm > 1e-12:
                xn, yn, zn = xyz / norm
            else:
                xn, yn, zn = 0.0, 0.0, 1.0
            out[f"{p}.theta"] = float(np.arctan2(yn, xn))
            out[f"{p}.phi"] = float(np.arccos(np.clip(zn, -1.0, 1.0)))
            i += 3
        return out


@dataclass
class PCAPreprocessor:
    """
    Optional PCA step applied *after* z-scoring by ComponentEncoder.

    Fit on the union of all encoded (z-scored) component vectors from all
    stimuli, then transforms each stimulus's (m_i, d) component matrix to
    (m_i, k).

    Back-projection maps a k-dim vector from PC space back to the original
    d-dim feature space (useful for reading ridge weights as original-feature
    loadings):
        w_feat = pca.components_.T @ w_pc    (pca.components_ is (k, d))

    Why PCA before regression?
      - Removes collinear directions (e.g. the three components of a spherical
        unit-vector are constrained to the unit sphere, so they span at most
        2D; PCA finds this automatically).
      - Puts the ridge penalty on decorrelated, variance-ordered directions
        rather than on correlated raw features.
      - Matches axis-coding papers (Chang & Tsao 2017) that first project
        stimuli onto PCs before fitting the linear model.
    """

    n_components: int
    _pca: Optional[PCA] = field(default=None, init=False, repr=False)

    @property
    def is_fit(self) -> bool:
        return self._pca is not None

    @property
    def explained_variance_ratio(self) -> Optional[np.ndarray]:
        return self._pca.explained_variance_ratio_ if self._pca is not None else None

    @property
    def n_components_actual(self) -> int:
        return int(self._pca.n_components_) if self._pca is not None else self.n_components

    def fit_transform(
        self, components_per_stim: list[np.ndarray]
    ) -> list[np.ndarray]:
        """
        Fit PCA on the stacked union of all component vectors, then return
        a new list where each (m_i, d) array is replaced by (m_i, k).
        """
        non_empty = [c for c in components_per_stim if len(c) > 0]
        if not non_empty:
            return components_per_stim
        all_comps = np.vstack(non_empty)
        k = min(self.n_components, all_comps.shape[1], max(all_comps.shape[0] - 1, 1))
        k = max(k, 1)
        self._pca = PCA(n_components=k)
        self._pca.fit(all_comps)
        return [
            self._pca.transform(c) if len(c) > 0 else np.zeros((0, k))
            for c in components_per_stim
        ]

    def back_project(self, v_pc: np.ndarray) -> np.ndarray:
        """
        Map a k-dim PC-space vector to the original d-dim feature space.

        Works for weights, axis directions, or any linear feature vector.
        Formula: w_feat = components_.T @ v_pc  (pca.components_ is (k, d)).
        """
        if self._pca is None:
            raise RuntimeError("PCAPreprocessor not fit. Call fit_transform() first.")
        return self._pca.components_.T @ v_pc

    def pc_feature_names(self) -> list[str]:
        """PC labels with explained-variance percentage, for display."""
        if self._pca is None:
            return []
        return [
            f"PC{i + 1} ({self._pca.explained_variance_ratio_[i]:.1%})"
            for i in range(self._pca.n_components_)
        ]


def _resolve_dotted(d: dict, key: str):
    """Resolve a dotted key like 'angularPosition.phi' against a nested dict."""
    cur = d
    for part in key.split("."):
        cur = cur[part]
    return cur


# Actual component dict structures (from mock_ga_responses.py + mock_rwa_plot.py):
#
#   Shaft:       {"angularPosition": {"theta":…, "phi":…},
#                 "orientation":     {"theta":…, "phi":…},
#                 "radialPosition":…, "length":…, "curvature":…, "radius":…}
#
#   Termination: {"angularPosition": {"theta":…, "phi":…},
#                 "direction":       {"theta":…, "phi":…},
#                 "radialPosition":…, "radius":…}
#
#   Junction:    {"angularPosition": {"theta":…, "phi":…},
#                 "angleBisectorDirection": {"theta":…, "phi":…},
#                 "radialPosition":…, "radius":…,
#                 "angularSubtense":…, "planarRotation":…}
#
# Spherical-pair fields (encoded as 3D unit vectors) are listed in
# ``*_SPHERICAL`` by base name. ``planarRotation`` is a planar angle and stays
# in ``*_CIRCULAR`` as a (cos, sin) pair.

SHAFT_LINEAR = ["radialPosition", "length", "curvature", "radius"]
SHAFT_CIRCULAR: list[str] = []
SHAFT_SPHERICAL = ["angularPosition", "orientation"]

TERMINATION_LINEAR = ["radialPosition", "radius"]
TERMINATION_CIRCULAR: list[str] = []
TERMINATION_SPHERICAL = ["angularPosition", "direction"]

JUNCTION_LINEAR = ["radialPosition", "radius", "angularSubtense"]
JUNCTION_CIRCULAR = ["planarRotation"]
JUNCTION_SPHERICAL = ["angularPosition", "angleBisectorDirection"]


def make_default_encoders() -> dict[str, ComponentEncoder]:
    """Return the per-type encoders with the default schemas."""
    return {
        "Shaft": ComponentEncoder(SHAFT_LINEAR, SHAFT_CIRCULAR, SHAFT_SPHERICAL),
        "Termination": ComponentEncoder(
            TERMINATION_LINEAR, TERMINATION_CIRCULAR, TERMINATION_SPHERICAL
        ),
        "Junction": ComponentEncoder(
            JUNCTION_LINEAR, JUNCTION_CIRCULAR, JUNCTION_SPHERICAL
        ),
    }

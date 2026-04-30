from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
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

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

    - Linear params are kept as-is.
    - Circular params (theta-like / phi-like) are encoded as (cos, sin) pairs so
      Euclidean distance respects circular topology.
    - After all stimuli have been encoded, call `fit_scaler` on the stacked array of
      every component from every stimulus, then `transform_with_scaler` on each row,
      so distances across components/stimuli live on the same scale.
    """

    linear_params: list[str]
    circular_params: list[str]
    scaler: Optional[StandardScaler] = None
    feature_names: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.feature_names:
            self.feature_names = self._build_feature_names()

    @property
    def n_features(self) -> int:
        return len(self.linear_params) + 2 * len(self.circular_params)

    def _build_feature_names(self) -> list[str]:
        names: list[str] = []
        for p in self.linear_params:
            names.append(p)
        for p in self.circular_params:
            names.append(f"{p}.cos")
            names.append(f"{p}.sin")
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
        return self.scaler.transform(encoded)


def _resolve_dotted(d: dict, key: str):
    """Resolve a dotted key like 'angularPosition.phi' against a nested dict."""
    cur = d
    for part in key.split("."):
        cur = cur[part]
    return cur


# Schemas matching the RWA dimensions defined in mock_rwa_analysis.py:49,86,114.
# theta-like/phi-like parameters are circular; everything else is linear.

SHAFT_LINEAR = ["radialPosition", "length", "curvature", "radius"]
SHAFT_CIRCULAR = ["theta", "angularPosition.phi", "orientation.phi"]

TERMINATION_LINEAR = ["radialPosition", "radius"]
TERMINATION_CIRCULAR = ["theta", "phi"]

JUNCTION_LINEAR = ["radialPosition", "radius", "angularSubtense"]
JUNCTION_CIRCULAR = ["theta", "phi", "planarRotation"]


def make_default_encoders() -> dict[str, ComponentEncoder]:
    """Return the per-type encoders with the default schemas."""
    return {
        "Shaft": ComponentEncoder(SHAFT_LINEAR, SHAFT_CIRCULAR),
        "Termination": ComponentEncoder(TERMINATION_LINEAR, TERMINATION_CIRCULAR),
        "Junction": ComponentEncoder(JUNCTION_LINEAR, JUNCTION_CIRCULAR),
    }

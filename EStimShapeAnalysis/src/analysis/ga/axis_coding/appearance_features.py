from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# Texture levels we one-hot encode. Anything outside this set is encoded as
# all-zero (no texture columns active) and a warning printed.
TEXTURE_LEVELS = ("SHADE", "SPECULAR", "2D")


@dataclass
class AppearanceFeatures:
    """
    Per-stimulus appearance features (texture one-hot + average RGB).

    Aligned by index to a list of stim_ids supplied at build time -- so a
    caller can stack this matrix next to the shape design matrix without
    further bookkeeping.
    """

    features: np.ndarray              # (n_stim, k)
    feature_names: list[str]          # length k
    texture_per_stim: list[Optional[str]]   # length n_stim, raw label or None
    n_missing_texture: int
    n_missing_rgb: int

    @property
    def n_stim(self) -> int:
        return self.features.shape[0]

    @property
    def n_features(self) -> int:
        return self.features.shape[1]

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        stim_ids,
        texture_col: str = "Texture",
        rgb_col_candidates: tuple[str, ...] = (
            "AverageRGB", "UnderlingAvgRGB", "UnderlyingAvgRGB", "UnderlyingAverageRGB",
        ),
    ) -> "AppearanceFeatures":
        """
        Pull texture and average-RGB for each stimulus in ``stim_ids``.

        Texture is one-hot encoded over (SHADE, SPECULAR, 2D); RGB is taken
        as a 3-vector in [0, 1].  Missing values become zeros and are counted
        for reporting; we don't drop stimuli here so alignment with the shape
        pipeline's stim_ids is preserved.
        """
        # Pick whichever RGB column is present.
        rgb_col = next(
            (c for c in rgb_col_candidates if c in df.columns), None
        )
        if texture_col not in df.columns and rgb_col is None:
            return cls(
                features=np.zeros((len(stim_ids), 0)),
                feature_names=[],
                texture_per_stim=[None] * len(stim_ids),
                n_missing_texture=len(stim_ids),
                n_missing_rgb=len(stim_ids),
            )

        # First-occurrence per StimSpecId for both columns (these are stim-level).
        keep_cols = ["StimSpecId"]
        if texture_col in df.columns:
            keep_cols.append(texture_col)
        if rgb_col is not None:
            keep_cols.append(rgb_col)

        sub = (
            df.dropna(subset=["StimSpecId"])
              .drop_duplicates(subset=["StimSpecId"])[keep_cols]
              .set_index("StimSpecId")
        )

        feat_names: list[str] = []
        if texture_col in df.columns:
            feat_names.extend([f"texture::{lvl}" for lvl in TEXTURE_LEVELS])
        if rgb_col is not None:
            feat_names.extend(["avgRGB::r", "avgRGB::g", "avgRGB::b"])

        features = np.zeros((len(stim_ids), len(feat_names)), dtype=np.float64)
        texture_per_stim: list[Optional[str]] = []
        n_missing_texture = 0
        n_missing_rgb = 0

        for i, sid in enumerate(stim_ids):
            row = sub.loc[sid] if sid in sub.index else None
            col = 0

            # Texture one-hot.
            if texture_col in df.columns:
                tex = (
                    _coerce_texture(row[texture_col])
                    if row is not None and texture_col in sub.columns
                    else None
                )
                texture_per_stim.append(tex)
                if tex is None:
                    n_missing_texture += 1
                else:
                    if tex in TEXTURE_LEVELS:
                        features[i, col + TEXTURE_LEVELS.index(tex)] = 1.0
                    # Unknown levels stay all-zero; counted as missing.
                    else:
                        n_missing_texture += 1
                col += len(TEXTURE_LEVELS)
            else:
                texture_per_stim.append(None)

            # Average RGB.
            if rgb_col is not None:
                rgb = _coerce_rgb(row[rgb_col]) if row is not None else None
                if rgb is None:
                    n_missing_rgb += 1
                else:
                    features[i, col:col + 3] = rgb

        return cls(
            features=features,
            feature_names=feat_names,
            texture_per_stim=texture_per_stim,
            n_missing_texture=n_missing_texture,
            n_missing_rgb=n_missing_rgb,
        )


def _coerce_texture(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, (tuple, list)) and len(value) >= 1:
        value = value[0]
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    if not isinstance(value, str):
        return None
    s = value.strip().upper()
    return s if s else None


def _coerce_rgb(value) -> Optional[np.ndarray]:
    """
    Accept several encodings: a length-3 sequence, a single-element tuple
    wrapping a length-3 sequence (matches the shape returned by
    ``UnderlingAvgRGBField.fetch_one``), or a string like '(0.4, 0.4, 0.4)'.
    Returns a length-3 ndarray clipped to [0, 1], or None.
    """
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    # fetch_one returns a 1-tuple of the row; the row itself may be a tuple.
    if isinstance(value, tuple) and len(value) == 1:
        value = value[0]
    if isinstance(value, str):
        s = value.strip().strip("()[]")
        try:
            parts = [float(x) for x in s.replace(",", " ").split() if x]
        except ValueError:
            return None
        if len(parts) != 3:
            return None
        value = parts
    if isinstance(value, (list, tuple, np.ndarray)):
        arr = np.asarray(value, dtype=np.float64).ravel()
        if arr.size != 3 or not np.all(np.isfinite(arr)):
            return None
        return np.clip(arr, 0.0, 1.0)
    return None

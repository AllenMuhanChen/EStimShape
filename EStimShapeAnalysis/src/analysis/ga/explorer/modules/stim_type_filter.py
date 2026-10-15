"""
Manual trial-type filter shared by explorer modules: one "Show <TYPE>"
checkbox per stim-type family.

Families: "_2D" versions count as their 3D type (REGIME_ONE_2D -> ONE);
SHUFFLE_PIXEL, SHUFFLE_PHASE, ... count as SHUFFLE; SIDETEST_2Dvs3D_* as
SIDETEST; LIGHTING* as LIGHTING; anything unknown as "other".
"""

from __future__ import annotations

import pandas as pd

from src.analysis.ga.explorer.explorer_module import Param

TYPE_FAMILIES = ["ZERO", "ONE", "TWO", "THREE", "VARIANTS", "DELTA", "SHUFFLE", "LIGHTING",
                 "SIDETEST", "CATCH", "BASELINE", "other"]
# Families hidden until ticked (Allen, 2026-10-08).
HIDDEN_BY_DEFAULT = {"SHUFFLE", "LIGHTING"}


def short_type(stim_type) -> str:
    """'REGIME_ESTIM_VARIANTS' -> 'VARIANTS', 'REGIME_ONE_2D' -> 'ONE_2D'."""
    t = str(stim_type or "?")
    for prefix in ("REGIME_ESTIM_", "REGIME_"):
        if t.startswith(prefix):
            return t[len(prefix):]
    return t


def type_family(stim_type) -> str:
    """'REGIME_ESTIM_VARIANTS' -> 'VARIANTS', 'REGIME_ONE_2D' -> 'ONE',
    'SHUFFLE_PIXEL' -> 'SHUFFLE', anything unknown -> 'other'."""
    t = short_type(stim_type)
    if t.endswith("_2D"):
        t = t[:-3]
    if t in TYPE_FAMILIES:
        return t
    for family in ("SHUFFLE", "LIGHTING", "SIDETEST", "CATCH"):
        if t.startswith(family):
            return family
    return "other"


def type_filter_params(families=TYPE_FAMILIES, hidden=HIDDEN_BY_DEFAULT,
                       what="stims", live=True) -> list[Param]:
    """One "Show <family>" checkbox per family (key ``type_<family>``)."""
    return [Param(f"type_{family}", f"Show {family}", "bool", family not in hidden,
                  live=live, tooltip=f"Show {family} {what}. _2D types count as their 3D type.")
            for family in families]


def shown_families(values: dict, families=TYPE_FAMILIES, hidden=HIDDEN_BY_DEFAULT) -> set:
    return {f for f in families if values.get(f"type_{f}", f not in hidden)}


def keep_types(stim_types: pd.Series, shown: set) -> pd.Series:
    """Boolean mask: which stim types belong to a shown family."""
    return stim_types.map(type_family).isin(shown)

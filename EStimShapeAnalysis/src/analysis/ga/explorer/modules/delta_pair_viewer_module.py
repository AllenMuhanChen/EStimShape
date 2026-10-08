"""
Delta-variant pair viewer (read-only).

Shows every delta next to the stimulus it was made from (its parent, the
"variant" of the pair): deltas on top, variants underneath, one pair per
column, with their mean responses and the delta/variant ratio. For each pair:
  - "in estim exp": whether the pair was included in the EStim experiment
    (IncludedDeltas.included for this delta + variant). Read-only.
  - "select": your own pick. "Make figure from selected" draws the picked
    pairs as a standalone figure (e.g. good examples of a component or a
    combination of components), which you can save.

Nothing is written to the GA database. Thresholds that decided inclusion for
the experiment are not used here: all delta-parent pairs with response data
are shown.

The red overlay on deltas marks the hypothesized component(s); it needs the
comp-map thumbnails that only some experiments generate, and silently does
nothing for the others.

The grid, selection and figure machinery is shared with the all pair
explorer (pair_viewer.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.ga.explorer.modules.pair_viewer import (PairViewerModule, mean_responses,
                                                          read_hypothesized_comp_rows)

DELTA_STIM_TYPE = "REGIME_ESTIM_DELTA"


def compute_delta_pairs(data: pd.DataFrame, response_col: str) -> pd.DataFrame | None:
    """Every REGIME_ESTIM_DELTA stim paired with its parent, with mean
    responses. No thresholds; pairs where either stim has no response data
    are left out."""
    mean_resp = mean_responses(data, response_col)
    info = data.drop_duplicates("StimSpecId").set_index("StimSpecId")
    deltas = info[info["StimType"] == DELTA_STIM_TYPE]
    rows = []
    for delta_id, parent_id in deltas["ParentId"].items():
        if parent_id not in mean_resp.index or delta_id not in mean_resp.index:
            continue
        rows.append({"ChildId": int(delta_id), "ParentId": int(parent_id),
                     "ChildType": DELTA_STIM_TYPE,
                     "ParentType": info["StimType"].get(parent_id),
                     "Child Response": float(mean_resp[delta_id]),
                     "Parent Response": float(mean_resp[parent_id])})
    if not rows:
        return None
    pairs = pd.DataFrame(rows)
    pairs["Ratio"] = pairs["Child Response"] / pairs["Parent Response"].replace(0, np.nan)
    return pairs


class DeltaPairViewerModule(PairViewerModule):
    name = "Delta-variant pairs"
    description = ("Every delta with the variant it was made from. 'in estim exp' "
                   "shows EStim inclusion (read-only); tick 'select' and press "
                   "'Make figure from selected' to build an example figure.")
    child_label = "Delta"
    parent_label = "Variant"
    child_prefix = "d"
    parent_prefix = "v"
    slug = "delta_pairs"

    def build_pairs(self, data, response_col):
        pairs = compute_delta_pairs(data, response_col)
        if pairs is None:
            return None
        # Overlay only on the delta: its hypothesized comp is the comp it changed.
        hyp = read_hypothesized_comp_rows()
        comps = {sid: c for sid, c in zip(hyp["StimId"], hyp["HypComps"]) if c}
        pairs["ChildComps"] = [comps.get(d) for d in pairs["ChildId"]]
        pairs["ParentComps"] = None
        pairs["Note"] = ""
        return pairs

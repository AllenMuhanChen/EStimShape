"""
All pair explorer (read-only).

Every parent-child pair that carries hypothesized-comp history: any stim with
a HypothesizedComp row (or the older StimCompsToPreserve), next to the parent
it was made from. That covers variant <- variant, variant <- ZERO/ONE/...,
delta <- variant, and stims of other types made from a parent that had a
hypothesis. Same grid as the delta-variant viewer: child on top, parent
underneath, mean responses and child/parent ratio, read-only "in estim exp",
"select" + "Make figure from selected", sorting by ratio/response/id/gen.

Two kinds of rows:
  - generated: the stim's own hypothesis, written when it was made (variants,
    deltas). The overlay shows the child's hypothesized comps on the child and
    the parent's on the parent (each in its own comp numbering).
  - inherited: GAStim copies the parent's row verbatim onto stims of other
    types (GAStim.chooseHypothesizedComp), so those rows hold the parent's
    hypothesis, not one about the child. The parent gets its comps overlaid;
    the child's comp numbering isn't known, so it gets none. The header says
    "inherited". Toggle them off with "Include inherited".

Trial types can each be shown or hidden ("Show ZERO", "Show SHUFFLE", ...);
a pair is shown only when both its child's and its parent's types are on.
SHUFFLE and LIGHTING are off by default.

No response or ratio thresholds; a pair is only left out when the child or
the parent has no response data. Nothing is written to any database.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.ga.explorer.explorer_module import Param
from src.analysis.ga.explorer.modules.pair_viewer import (PairViewerModule, _fmt,
                                                          mean_responses,
                                                          read_hypothesized_comp_rows)
from src.analysis.ga.explorer.modules.stim_type_filter import TYPE_FAMILIES as ALL_FAMILIES
from src.analysis.ga.explorer.modules.stim_type_filter import (short_type, shown_families,
                                                               type_family,
                                                               type_filter_params)

# No BASELINE checkbox here: baseline stims never have hypothesized comps.
TYPE_FAMILIES = [f for f in ALL_FAMILIES if f != "BASELINE"]
TYPE_FILTERS = ["any"] + TYPE_FAMILIES


def compute_hypothesis_pairs(data: pd.DataFrame, response_col: str) -> pd.DataFrame | None:
    """One pair per stim that has a hypothesized-comp row and whose parent
    (repository ParentId) also has response data."""
    hyp = read_hypothesized_comp_rows()
    if hyp.empty:
        return None
    mean_resp = mean_responses(data, response_col)
    info = data.drop_duplicates("StimSpecId").set_index("StimSpecId")
    own = dict(zip(hyp["StimId"], hyp["HypComps"]))
    rows = []
    for r in hyp.itertuples(index=False):
        child = r.StimId
        if child not in mean_resp.index or child not in info.index:
            continue
        parent = info.at[child, "ParentId"]
        if pd.isna(parent) or int(parent) not in mean_resp.index:
            continue
        parent = int(parent)
        inherited = r.RowParentId is not None and r.RowParentId != parent
        if inherited:
            # The row is the parent's own (copied); comps are in the parent's numbering.
            child_comps = None
            parent_comps = own.get(parent) or r.HypComps or None
        else:
            child_comps = r.HypComps or None
            parent_comps = r.ParentHypComps or None
        rows.append({"ChildId": child, "ParentId": parent,
                     "ChildType": info.at[child, "StimType"],
                     "ParentType": info["StimType"].get(parent),
                     "Child Response": float(mean_resp[child]),
                     "Parent Response": float(mean_resp[parent]),
                     "ChildComps": child_comps, "ParentComps": parent_comps,
                     "Note": "inherited" if inherited else ""})
    if not rows:
        return None
    pairs = pd.DataFrame(rows)
    pairs["Ratio"] = pairs["Child Response"] / pairs["Parent Response"].replace(0, np.nan)
    return pairs


class AllPairExplorerModule(PairViewerModule):
    name = "All pair explorer"
    description = ("Every parent-child pair with hypothesized-comp history, e.g. "
                   "variant from variant, delta from variant, variant from ONE. "
                   "SHUFFLE and LIGHTING are hidden until ticked. Same selection "
                   "and figure as the delta-variant viewer.")
    child_label = "Child"
    parent_label = "Parent"
    child_prefix = "c"
    parent_prefix = "p"
    slug = "all_pairs"

    def extra_params(self):
        return [
            # One on/off per trial type: a pair is shown only when both its
            # child's and its parent's types are ticked.
            *type_filter_params(TYPE_FAMILIES, what="pairs (child or parent)"),
            Param("child_type", "Child type", "choice", "any", choices=TYPE_FILTERS, live=True,
                  tooltip="Only pairs whose child is this type. _2D types count as "
                          "their 3D type."),
            Param("parent_type", "Parent type", "choice", "any", choices=TYPE_FILTERS, live=True),
            Param("include_inherited", "Include inherited", "bool", True, live=True,
                  tooltip="Pairs whose child only carries a copy of its parent's "
                          "hypothesis (stims of other types made from it). The child "
                          "gets no overlay."),
        ]

    def build_pairs(self, data, response_col):
        return compute_hypothesis_pairs(data, response_col)

    def filter_pairs(self, df):
        v = self.values
        shown = shown_families(v, TYPE_FAMILIES)
        df = df[df["ChildType"].map(type_family).isin(shown)
                & df["ParentType"].map(type_family).isin(shown)]
        if v.get("child_type", "any") != "any":
            df = df[df["ChildType"].map(type_family) == v["child_type"]]
        if v.get("parent_type", "any") != "any":
            df = df[df["ParentType"].map(type_family) == v["parent_type"]]
        if not v.get("include_inherited", True):
            df = df[df["Note"] != "inherited"]
        return df

    def header_text(self, r):
        note = f"  ({r['Note']})" if r["Note"] else ""
        return (f"{short_type(r['ChildType'])} ← {short_type(r['ParentType'])}\n"
                f"ratio {_fmt(r['Ratio'], '.2f')}{note}")

from __future__ import annotations

import time
from enum import Enum
from typing import List

from clat.util import time_util

from src.pga.ga_classes import Lineage, Stimulus, SideTest
from src.pga.stim_types import is_mutatable, is_3d


class ShuffleType(Enum):
    """The shuffle mutation types. The string values are read on the Java side
    (FromDbGABlockGenerator -> ShuffleGAStim) to pick which shuffle script to run.

    PIXEL preserves the shape's boundary contour and shuffles only the interior; WHOLE_CONTOUR_PIXEL
    shuffles the whole shape including the boundary (same pixel_shuffle.py script, --whole-contour)."""
    PIXEL = "SHUFFLE_PIXEL"
    WHOLE_CONTOUR_PIXEL = "SHUFFLE_WHOLE_CONTOUR_PIXEL"
    PHASE = "SHUFFLE_PHASE"
    MAGNITUDE = "SHUFFLE_MAGNITUDE"


class ShuffleSideTest(SideTest):
    """
    Side test that takes the top-N responders from the previous generation and, for each,
    makes one shuffle of every ShuffleType (interior pixel, whole-contour pixel, phase, and
    magnitude) of the parent (preserving the parent's texture and color).

    This replaces the old post-hoc ShuffleTrialGenerator: instead of binning across the whole
    experiment after the fact, every generation we shuffle the current top responder(s) so we
    always have shuffle controls no matter when the GA stops.

    The Java side reproduces the parent stimulus and runs the matching shuffle script on the
    rendered image, keyed off the SHUFFLE_<TYPE> mutation_type written here.

    Only 3D stimuli are shuffled - shuffling a flat 2D stimulus would make no sense.
    """

    def __init__(self, *, conn, n_top_responders: int = 1):
        self.conn = conn
        self.n_top_responders = n_top_responders

    def run(self, lineages: List[Lineage], gen_id: int):
        top_responders, lineage_for_stim_id = self._collect_top_responders(lineages, gen_id)
        for parent in top_responders:
            self._make_shuffles(parent, lineage_for_stim_id[parent.id], gen_id)

    def _collect_top_responders(self, lineages: List[Lineage], gen_id: int):
        # Pool previous-generation stimuli across all lineages, remembering each stim's lineage.
        candidates: List[Stimulus] = []
        lineage_for_stim_id = {}
        for lineage in lineages:
            for stim in lineage.stimuli:
                if stim.gen_id != gen_id - 1:
                    continue
                if stim.response_rate is None:
                    continue
                # Excludes baseline, catch, shuffle, ... (see is_mutatable); a shuffle is never
                # itself shuffled.
                if not is_mutatable(stim):
                    continue
                # Only shuffle 3D stimuli - a flat 2D stimulus has nothing meaningful to shuffle.
                if not is_3d(self.conn, stim.id):
                    continue
                candidates.append(stim)
                lineage_for_stim_id[stim.id] = lineage

        # Take the N highest responders across the whole previous generation.
        top_responders = sorted(candidates, key=lambda s: s.response_rate, reverse=True)[:self.n_top_responders]
        return top_responders, lineage_for_stim_id

    def _make_shuffles(self, parent: Stimulus, lineage: Lineage, gen_id: int):
        for shuffle_type in ShuffleType:
            new_stimulus = Stimulus(time_util.now(),
                                    shuffle_type.value,
                                    mutation_magnitude=None,
                                    gen_id=gen_id,
                                    parent_id=parent.id)
            time.sleep(0.001)
            lineage.tree.add_child_to(parent, new_stimulus)
            lineage.stimuli.append(new_stimulus)

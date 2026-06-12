from __future__ import annotations

import time
from typing import List, Sequence

from clat.util import time_util

from src.pga.ga_classes import Lineage, Stimulus, SideTest
from src.pga.stim_types import is_mutatable, is_3d


# Single mutation_type for all lighting variants. The specific lighting direction is carried in
# the stimulus's mutation_magnitude (the rotation angle in degrees about the vertical axis),
# rather than baked into the type string - so new directions/angles need no new types.
LIGHTING_MUTATION_TYPE = "LIGHTING"

# Default directions: 45 degrees left and right of the front light {0, 0, 500, 1}. The front-lit
# version is just the normal stimulus, so we only generate the rotated ones.
DEFAULT_LIGHTING_ANGLES = (-45.0, 45.0)


class LightingSideTest(SideTest):
    """
    Side test that takes the top-N (default 1) 3D responder(s) from the previous generation and,
    for each, re-renders the same shape under additional lighting directions.

    Carries the old AlexNet LightingPostHocGenerator idea into the neural GA: instead of a
    post-hoc sweep, every generation we light-probe the current top 3D stimulus so we always
    have lighting-direction controls no matter when the GA stops.

    Each variant is a stimulus with mutation_type "LIGHTING" and mutation_magnitude set to its
    rotation angle in degrees; the Java side (FromDbGABlockGenerator -> LightingGAStim) rotates
    the front light {0, 0, 500, 1} by that angle about the vertical axis.

    Only 3D stimuli are used - lighting direction is meaningless for flat 2D stimuli.
    """

    def __init__(self, *, conn, n_top_responders: int = 1,
                 light_angles: Sequence[float] = DEFAULT_LIGHTING_ANGLES):
        self.conn = conn
        self.n_top_responders = n_top_responders
        self.light_angles = light_angles

    def run(self, lineages: List[Lineage], gen_id: int):
        top_responders, lineage_for_stim_id = self._collect_top_responders(lineages, gen_id)
        for parent in top_responders:
            self._make_lighting_variants(parent, lineage_for_stim_id[parent.id], gen_id)

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
                # Excludes baseline, catch, shuffle, lighting, ... (see is_mutatable).
                if not is_mutatable(stim):
                    continue
                # Lighting direction only makes sense for 3D stimuli.
                if not is_3d(self.conn, stim.id):
                    continue
                candidates.append(stim)
                lineage_for_stim_id[stim.id] = lineage

        # Take the N highest 3D responders across the whole previous generation.
        top_responders = sorted(candidates, key=lambda s: s.response_rate, reverse=True)[:self.n_top_responders]
        return top_responders, lineage_for_stim_id

    def _make_lighting_variants(self, parent: Stimulus, lineage: Lineage, gen_id: int):
        for angle in self.light_angles:
            new_stimulus = Stimulus(time_util.now(),
                                    LIGHTING_MUTATION_TYPE,
                                    mutation_magnitude=angle,
                                    gen_id=gen_id,
                                    parent_id=parent.id)
            time.sleep(0.001)
            lineage.tree.add_child_to(parent, new_stimulus)
            lineage.stimuli.append(new_stimulus)

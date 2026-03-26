import time
from typing import List

from clat.util import time_util
from src.pga.ga_classes import SideTest, Lineage, Stimulus
from src.pga.stim_types import StimType


def is_regime_zero(stim):
    return stim.mutation_type == StimType.REGIME_ZERO.value or stim.mutation_type == StimType.REGIME_ZERO_2D.value


class BaseLineSideTest(SideTest):
    def run(self, lineages: List[Lineage], gen_id: int):
        # eligible stimuli are gen_id=1 and regime zero
        lineages_for_stim_id: dict[int, Lineage] = {}
        eligible_stim : list[Stimulus] = []
        for lineage in lineages:
            for stim in lineage.stimuli:
                if stim.gen_id == 1 and is_regime_zero(stim):
                    eligible_stim.append(stim)
                    lineages_for_stim_id[stim.id] = lineage

        # take the lowest response, highest response, 20 percentile, 40 percentile, 60 percentile, and 80 percentile
        eligible_stim.sort(key=lambda s: s.response_rate)

        n = len(eligible_stim)
        indices = {
            0,  # lowest
            n - 1,  # highest
            int(n * 0.2),  # 20th percentile
            int(n * 0.4),  # 40th percentile
            int(n * 0.6),  # 60th percentile
            int(n * 0.8),  # 80th percentile
        }
        selected_stim = [eligible_stim[i] for i in sorted(indices)]

        for stim in selected_stim:
            new_stim = Stimulus(
                time_util.now(),
                StimType.BASELINE.value,
                mutation_magnitude=0,
                gen_id=gen_id,
                parent_id=stim.id
            )
            time.sleep(0.001)
            lineages_for_stim_id[stim.id].tree.add_child_to(stim, new_stim)
            lineages_for_stim_id[stim.id].stimuli.append(new_stim)









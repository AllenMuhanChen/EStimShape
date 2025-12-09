from typing import Callable, List

from src.pga.config.simultaneous_2dvs3d_config import Simultaneous3Dvs2DConfig
from src.pga.ga_classes import Phase, MutationAssigner, Lineage, Stimulus, ParentSelector, MutationMagnitudeAssigner, \
    RegimeTransitioner
from src.pga.regime_one import calculate_peak_response
from src.pga.stim_types import StimType

class EStimShapeConfig(Simultaneous3Dvs2DConfig):
    """
    Configuration to add a fourth phase to make variants of stimuli to test in EStimShape.
    """
    def make_phases(self):
        return [self.seeding_phase(),
                self.zooming_phase(),
                self.growing_phase(),
                self.estim_variant_phase()
                ]

    def estim_variant_phase(self):
        return Phase(
            EStimPhaseParentSelector(
                get_all_stimuli_func=self.get_all_stimuli_func(),
                threshold=0.75),
            EStimPhaseMutationAssigner(),
            EStimPhaseMagnitudeAssigner(),
            EStimPhaseTransitioner(),
        )

class EStimPhaseParentSelector(ParentSelector):
    get_all_stimuli_func: Callable[[], List[Stimulus]]
    threshold: float
    def __init__(self, *, get_all_stimuli_func: Callable[[], List[Stimulus]], threshold: float) -> None:
        self.get_all_stimuli_func = get_all_stimuli_func
        self.threshold = threshold


    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        # eligible parents = within x% of the peak response?
        all_stim_across_lineages = self.get_all_stimuli_func()
        all_responses_across_lineages = [s.response_rate for s in all_stim_across_lineages]
        peak_response = calculate_peak_response(all_responses_across_lineages, across_n=1)
        threshold_response = float(peak_response) * self.threshold

        passing_threshold = [s for s in lineage.stimuli if s.response_rate > threshold_response]
        return passing_threshold



class EStimPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage: Lineage, parent: Stimulus):
        return StimType.REGIME_ESTIM_VARIANTS.value


class EStimPhaseMagnitudeAssigner(MutationMagnitudeAssigner):
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        return 0


class EStimPhaseTransitioner(RegimeTransitioner):
    def should_transition(self, lineage: Lineage) -> bool:
        return False




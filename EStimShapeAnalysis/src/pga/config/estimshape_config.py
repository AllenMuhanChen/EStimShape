from typing import Callable, List, Type

import numpy as np

from src.pga.config.simultaneous_2dvs3d_config import Simultaneous3Dvs2DConfig
from src.pga.ga_classes import Phase, MutationAssigner, Lineage, Stimulus, ParentSelector, MutationMagnitudeAssigner, \
    RegimeTransitioner
from src.pga.regime_one import calculate_peak_response, GrowingPhaseMutationMagnitudeAssigner, \
    GrowingPhaseParentSelector, GrowingPhaseTransitioner
from src.pga.stim_types import StimType


class EStimShapeConfig(Simultaneous3Dvs2DConfig):
    """
    Configuration to add a fourth phase to make variants of stimuli to test in EStimShape.
    """
    def __init__(self, *, is_alexnet_mock, database: str, base_intan_path: str, java_output_dir: str,
                 allen_dist_dir: str):
        super().__init__(is_alexnet_mock=is_alexnet_mock, database=database, base_intan_path=base_intan_path, java_output_dir=java_output_dir, allen_dist_dir=allen_dist_dir)

    def make_phases(self):
        return [self.seeding_phase(),
                self.zooming_phase(),
                self.growing_phase(),
                self.estim_variant_phase()
                ]

    def growing_phase_transitioner(self) -> type[RegimeTransitioner]:
        if self.is_alexnet_mock:
            return MockGrowingPhaseTransitioner()
        else:
            return super().growing_phase_transitioner()

    def estim_variant_phase(self):
        return Phase(
            EStimPhaseParentSelector(
                get_all_stimuli_func=self.get_all_stimuli_func(),
                threshold=0.50),
            EStimPhaseMutationAssigner(),
            EStimPhaseMagnitudeAssigner(),
            EStimPhaseTransitioner(),
        )


class MockGrowingPhaseTransitioner(RegimeTransitioner):
    def should_transition(self, lineage: Lineage) -> bool:
        return True


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

        # If no stimuli pass threshold, return empty list or handle edge case
        if not passing_threshold:
            return []


        # assign score
        # calculate bonus
        variant_response_sum = sum([s.response_rate for s in passing_threshold if s.mutation_type == StimType.REGIME_ESTIM_VARIANTS.value])
        total_response_sum = sum([s.response_rate for s in passing_threshold])
        variant_response_proportion = variant_response_sum / total_response_sum
        target_variant_chance = 0.9
        if variant_response_proportion != 0:
            # avoid divide by 0
            bonus = target_variant_chance / variant_response_proportion
        else:
            bonus = 1

        #assign scores, adding bonus only if parent is a variant
        scores = []
        for s in passing_threshold:
            if s.mutation_type == StimType.REGIME_ESTIM_VARIANTS.value:
                scores.append(s.response_rate * bonus)
            else:
                scores.append(s.response_rate)

        scores = np.array(scores)
        # Normalize response rates to create sampling probabilities
        probabilities = scores / scores.sum()

        # Sample stimuli based on their normalized response rates
        selected_indices = np.random.choice(
            len(passing_threshold),
            size=batch_size,
            replace=True,
            p=probabilities
        )

        return [passing_threshold[i] for i in selected_indices]



class EStimPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage: Lineage, parent: Stimulus):
        return StimType.REGIME_ESTIM_VARIANTS.value


class EStimPhaseMagnitudeAssigner(MutationMagnitudeAssigner):
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        return 0


class EStimPhaseTransitioner(RegimeTransitioner):
    def should_transition(self, lineage: Lineage) -> bool:
        return False




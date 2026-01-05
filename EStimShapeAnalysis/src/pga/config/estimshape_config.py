import time
from typing import Callable, List, Type

import numpy as np

from clat.util import time_util
from src.pga.config.simultaneous_2dvs3d_config import Simultaneous3Dvs2DConfig, DnessSideTest
from src.pga.ga_classes import Phase, MutationAssigner, Lineage, Stimulus, ParentSelector, MutationMagnitudeAssigner, \
    RegimeTransitioner, SideTest
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

    def side_tests(self):
        return [DnessSideTest(n_top_3d=4, n_top_2d=4),
                EStimVariantDeltaSideTest()]

    def growing_phase_transitioner(self) -> type[RegimeTransitioner]:
        if self.is_alexnet_mock:
            return MockGrowingPhaseTransitioner()
        else:
            return super().growing_phase_transitioner()

    def estim_variant_phase(self):
        return Phase(
            EStimPhaseParentSelector(
                get_all_stimuli_func=self.get_all_stimuli_func(),
                threshold=0.75),
            EStimPhaseMutationAssigner(),
            EStimPhaseMagnitudeAssigner(),
            EStimPhaseTransitioner(),
        )


class MockGrowingPhaseTransitioner(RegimeTransitioner):
    num_times = 0
    def should_transition(self, lineage: Lineage) -> bool:
        self.num_times+=1
        if self.num_times > 3:
            return True
        else:
            return False


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
        min_response = min(all_responses_across_lineages)
        floored_responses = [s.response_rate - min_response for s in all_stim_across_lineages]
        max_response = max(floored_responses)
        normalized_responses = [r / max_response for r in floored_responses]
        peak_normalized_response = calculate_peak_response(normalized_responses, across_n=1)

        threshold_response = (float(peak_normalized_response) * self.threshold) * max_response + min_response

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

class EStimVariantDeltaSideTest(SideTest):
    num_deltas_per_variant = 1


    def run(self, lineages: List[Lineage], gen_id: int):
        #identify eligible stimuli (variants)
        variant_stimuli : List[Stimulus] = []

        for lineage in lineages:
            for stim in lineage.stimuli:
                if stim.mutation_type == StimType.REGIME_ESTIM_VARIANTS.value:
                    if stim.response_rate is not None:
                        variant_stimuli.append(stim)
                        stim.lineage = lineage

        #filter out via response rate
        max_response_stim = max(variant_stimuli, key=lambda s: s.response_rate)
        threshold = max_response_stim.response_rate * 0.6

        past_threshold_stim: List[Stimulus] = []
        for s in variant_stimuli:
            if s.response_rate >= threshold:
                past_threshold_stim.append(s)

        #filter out ones that have been tested enough already
            #first make dict of deltas for variants
        deltas_for_variants = {} #store all deltas we have for eligible stimuli
        for candidate_parent in past_threshold_stim:
            # look for other children with the same parent_id
            for lineage in lineages:
                for stim in lineage.stimuli:
                    if stim.parent_id == candidate_parent.id and stim.mutation_type == StimType.REGIME_ESTIM_DELTA.value:
                        if deltas_for_variants[candidate_parent.id] is None:
                            deltas_for_variants[candidate_parent.id] = []
                        deltas_for_variants[candidate_parent.id].extend(stim)

        #TODO: check existing deltas for compatibility (can't accidentally have too high resp rate)


            #go through eligible stimuli and check
        eligible_stimuli : List[Stimulus] = []
        for candidate_parent in past_threshold_stim:
            no_deltas_for_variant = not candidate_parent.id in deltas_for_variants
            too_few_deltas_for_variant = False
            if not no_deltas_for_variant:
                too_few_deltas_for_variant = len(deltas_for_variants[candidate_parent.id]) < self.num_deltas_per_variant
            if no_deltas_for_variant or too_few_deltas_for_variant:
                eligible_stimuli.append(candidate_parent)


        #add to lineage
        for candidate_parent in eligible_stimuli:
            new_stimulus = Stimulus(time_util.now(),
                                    StimType.REGIME_ESTIM_DELTA.value,
                                    mutation_magnitude=0,
                                    gen_id=gen_id,
                                    parent_id=candidate_parent.id
                                    )
            time.sleep(0.001)
            candidate_parent.lineage.tree.add_child_to(candidate_parent, new_stimulus) #we added .lineage manually
            candidate_parent.lineage.stimuli.append(new_stimulus)


        #TODO: add /update a table designed to hold this info for easier analysis



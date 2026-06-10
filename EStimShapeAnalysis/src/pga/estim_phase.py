import random
import time
from dataclasses import dataclass
from typing import Callable, List, Dict, Type

import numpy as np

from clat.util import time_util, connection
from src.pga.ga_classes import ParentSelector, Stimulus, Lineage, MutationAssigner, MutationMagnitudeAssigner, \
    RegimeTransitioner, SideTest
from src.pga.regime_one import calculate_peak_response
from src.pga.stim_types import StimType


def _hypothesized_comp_table(connection: Type[connection]) -> str:
    # Renamed from StimCompsToPreserve to HypothesizedComp; fall back for old, un-migrated DBs.
    connection.execute("SHOW TABLES LIKE 'HypothesizedComp'")
    return "HypothesizedComp" if connection.fetch_one() else "StimCompsToPreserve"


def has_preservation_history(connection: Type[connection], id: int) -> bool:
    """
    Check if the stimulus with the given ID has a hypothesized-component history in the database.
    """
    table = _hypothesized_comp_table(connection)
    connection.execute(f"SELECT COUNT(*) FROM {table} WHERE stim_id = %s", (id,))
    num_entries = connection.fetch_one()
    return num_entries > 0


@dataclass
class EStimPhaseParentSelector(ParentSelector):
    get_all_stimuli_func: Callable[[], List[Stimulus]]
    threshold: float
    conn: Type[connection]


    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        # eligible parents = within x% of the peak response?
        all_stim_across_lineages = self.get_all_stimuli_func()
        #remove response rate is none
        all_stim_across_lineages = [s for s in all_stim_across_lineages if s.response_rate is not None]

        #remove baselines
        for stimulus in all_stim_across_lineages:
            if stimulus.mutation_type == StimType.BASELINE.value:
                all_stim_across_lineages.remove(stimulus)


        # 260325_0 change ONLY
        # all_stim_across_lineages = [s for s in all_stim_across_lineages if s.gen_id>1]


        all_responses_across_lineages = [s.response_rate for s in all_stim_across_lineages if s.response_rate is not None]
        min_response = min(all_responses_across_lineages)
        floored_responses = [s.response_rate - min_response for s in all_stim_across_lineages if s.response_rate is not None]
        max_response = max(floored_responses)
        normalized_responses = [r / max_response for r in floored_responses]
        peak_normalized_response = calculate_peak_response(normalized_responses, across_n=1)

        threshold_response = (float(peak_normalized_response) * self.threshold) * max_response + min_response

        passing_threshold = [s for s in lineage.stimuli if s.response_rate is not None and s.response_rate > threshold_response ]

        # If no stimuli pass threshold, return empty list or handle edge case
        if not passing_threshold:
            return []


        # assign score
        # calculate bonus
        variant_response_sum = sum([s.response_rate for s in passing_threshold if self.has_preservation_history(s.id)])
        total_response_sum = sum([s.response_rate for s in passing_threshold])
        variant_response_proportion = variant_response_sum / total_response_sum
        target_variant_chance = 0.9
        if variant_response_proportion != 0:
            # avoid divide by 0
            bonus = target_variant_chance / variant_response_proportion
        else:
            bonus = 1

        #assign scores, adding bonus only if parent is a variant or is descended from a variant
        scores = []
        for s in passing_threshold:
            if self.has_preservation_history(s.id):
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

    def has_preservation_history(self, id: int) -> bool:
        """
        Check if the stimulus with the given ID has a preservation history in the database.
        """
        has_preservation_history(self.conn, id)

class EStimPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage: Lineage, parent: Stimulus):
        return StimType.REGIME_ESTIM_VARIANTS.value


class EStimPhaseMagnitudeAssigner(MutationMagnitudeAssigner):
    """
    With probability `chance` returns a magnitude drawn uniformly from
    [min_magnitude, max_magnitude]; otherwise returns 0. A nonzero magnitude
    instructs the Java side to apply a slight mutation to the variant's
    preserved limb.
    """

    def __init__(self, chance: float = 0.5, min_magnitude: float = 0.05, max_magnitude: float = 0.15):
        self.chance = chance
        self.min_magnitude = min_magnitude
        self.max_magnitude = max_magnitude

    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        if random.random() < self.chance:
            return random.uniform(self.min_magnitude, self.max_magnitude)
        return 0


class EStimPhaseTransitioner(RegimeTransitioner):
    def should_transition(self, lineage: Lineage) -> bool:
        return False


@dataclass
class EStimVariantSideTest(SideTest):
    get_all_stim_func: Callable[[], List[Stimulus]]
    conn: Type[connection]
    threshold: float = 0.5
    max_stim_per_lineage: int = 2
    magnitude_assigner: MutationMagnitudeAssigner = None

    def __post_init__(self):
        if self.magnitude_assigner is None:
            self.magnitude_assigner = EStimPhaseMagnitudeAssigner()

    def run(self, lineages: List[Lineage], gen_id: int):
        selector = EStimPhaseParentSelector(self.get_all_stim_func, self.threshold, self.conn)
        for lineage in lineages:
            if lineage.current_regime_index > 1 and len(lineage.stimuli) > 5:
                chosen_parents = selector.select_parents(lineage, batch_size=self.max_stim_per_lineage)
                for parent in chosen_parents:
                    new_stimulus = Stimulus(time_util.now(),
                                            StimType.REGIME_ESTIM_VARIANTS.value,
                                            mutation_magnitude=self.magnitude_assigner.assign_mutation_magnitude(
                                                lineage, parent),
                                            gen_id=gen_id,
                                            parent_id=parent.id
                                            )
                    time.sleep(0.001)
                    lineage.tree.add_child_to(parent, new_stimulus)
                    lineage.stimuli.append(new_stimulus)



class EStimVariantDeltaSideTest(SideTest):
    def __init__(self, num_deltas_per_variant: int = 1, delta_resp_ratio_threshold: float = 0.5,
                 max_attempts_per_variant_multiplier: int = 3, conn=Type[connection],
                 min_magnitude: float = 0.3, max_magnitude: float = 0.8,
                 max_deltas_per_generation: int = None):
        self.num_deltas_per_variant = num_deltas_per_variant
        self.delta_resp_ratio_threshold = delta_resp_ratio_threshold
        self.max_attempts_per_variant_multiplier = max_attempts_per_variant_multiplier
        self.conn = conn
        # Mutation magnitude for deltas is decided here (Python) rather than on the Java side,
        # mirroring how the rest of the GA assigns magnitudes. Drawn uniformly from
        # [min_magnitude, max_magnitude]. Discreteness is still chosen randomly on the Java side.
        self.min_magnitude = min_magnitude
        self.max_magnitude = max_magnitude
        # Optional ceiling on how many deltas to create across all parents in a single generation.
        # None means uncapped. When capped, higher-response parents are served first.
        self.max_deltas_per_generation = max_deltas_per_generation

    def assign_mutation_magnitude(self) -> float:
        return random.uniform(self.min_magnitude, self.max_magnitude)

    def run(self, lineages: List[Lineage], gen_id: int):
        #identify eligible stimuli (variants)
        # regimes = [l.current_regime_index for l in lineages]
        # if max(regimes) < 3:
        #     return
        # Deltas can be made from any non-baseline stimulus, not just variants: a high-response
        # delta or regime_one stim is still worth driving down with a delta. Whatever a delta is
        # made from plays the "variant" role for that pair. The response threshold below keeps us
        # to high-response parents.
        candidate_parents : List[Stimulus] = []
        lineages_for_stim_id = {}
        for lineage in lineages:
            for stim in lineage.stimuli:
                if stim.mutation_type != StimType.BASELINE.value and stim.response_rate is not None:
                    candidate_parents.append(stim)
                    lineages_for_stim_id[stim.id] = lineage
        if len(candidate_parents) == 0:
            return
        #filter out via response rate
        max_response_stim = max(candidate_parents, key=lambda s: s.response_rate)
        threshold = max_response_stim.response_rate * 0.6

        past_threshold_stim: List[Stimulus] = []
        for s in candidate_parents:
            if s.response_rate >= threshold:
                past_threshold_stim.append(s)
        # Serve higher-response parents first so the per-generation cap (if any) goes to them.
        past_threshold_stim.sort(key=lambda s: s.response_rate, reverse=True)

        #filter out ones that have been tested enough already
            #first make dict of deltas for variants
        deltas_for_variants : Dict[int, List[Stimulus]]= {} #store all deltas we have for eligible stimuli
        stim_for_stim_id: Dict[int, Stimulus] = {}
        for candidate_parent in past_threshold_stim:
            # look for other children with the same parent_id
            stim_for_stim_id[candidate_parent.id] = candidate_parent
            for lineage in lineages:
                for stim in lineage.stimuli:
                    if stim.parent_id == candidate_parent.id and stim.mutation_type == StimType.REGIME_ESTIM_DELTA.value:
                        if candidate_parent.id not in deltas_for_variants:
                            deltas_for_variants[candidate_parent.id] = []
                        deltas_for_variants[candidate_parent.id].append(stim)


        #check existing deltas for compatibility (can't accidentally have too high resp rate)
        eligible_deltas_for_variants : Dict[int, List[Stimulus]] = {}
        for variant_id, deltas in deltas_for_variants.items():
            # get resp for variant_id
            variant_resp = stim_for_stim_id[variant_id].response_rate
            for delta in deltas:
                delta_resp = delta.response_rate
                if delta_resp is None or variant_resp is None:
                    continue
                if delta_resp / variant_resp < self.delta_resp_ratio_threshold:
                    if variant_id not in eligible_deltas_for_variants:
                        eligible_deltas_for_variants[variant_id] = []
                    eligible_deltas_for_variants[variant_id].append(delta)
            # get resp for delta
            # check if meets threshold



        #go through eligible stimuli and check
        # a parent simply gets deltas (each mutating one of the
        # parent's hypothesized comps, decided Java-side) until enough pass the response-drop
        # threshold or the attempt budget runs out. Failed (high-response) deltas pass the parent
        # threshold themselves, so chaining deltas onto deltas explores the remaining components.
        max_attempts_per_variant = self.max_attempts_per_variant_multiplier * self.num_deltas_per_variant
        eligible_stimuli : List[Stimulus] = []
        for candidate_parent in past_threshold_stim:
            num_eligible_deltas = len(eligible_deltas_for_variants.get(candidate_parent.id, []))
            if num_eligible_deltas >= self.num_deltas_per_variant:
                continue  # already have enough deltas that drop the response

            all_deltas = deltas_for_variants.get(candidate_parent.id, [])
            num_responded = len([d for d in all_deltas if d.response_rate is not None])
            num_in_flight = len(all_deltas) - num_responded

            # stop trying if we've already attempted too many times
            remaining_attempts = max_attempts_per_variant - len(all_deltas)
            if remaining_attempts <= 0:
                continue

            # Don't double-make: account for deltas already in flight toward the target.
            number_of_deltas_to_make = self.num_deltas_per_variant - num_eligible_deltas - num_in_flight
            number_of_deltas_to_make = min(number_of_deltas_to_make, remaining_attempts)
            if number_of_deltas_to_make <= 0:
                continue

            for i in range(number_of_deltas_to_make):
                eligible_stimuli.append(candidate_parent)

        # Cap total deltas this generation. eligible_stimuli is already ordered by parent response
        # (highest first), so truncating keeps the highest-response parents' deltas.
        if self.max_deltas_per_generation is not None:
            eligible_stimuli = eligible_stimuli[:self.max_deltas_per_generation]

        #add to lineage
        for candidate_parent in eligible_stimuli:
            new_stimulus = Stimulus(time_util.now(),
                                    StimType.REGIME_ESTIM_DELTA.value,
                                    mutation_magnitude=self.assign_mutation_magnitude(),
                                    gen_id=gen_id,
                                    parent_id=candidate_parent.id
                                    )
            time.sleep(0.001)
            lineages_for_stim_id[candidate_parent.id].tree.add_child_to(candidate_parent, new_stimulus) #we added .lineage manually
            lineages_for_stim_id[candidate_parent.id].stimuli.append(new_stimulus)

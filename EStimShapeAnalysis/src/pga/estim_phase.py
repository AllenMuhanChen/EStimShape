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


def _read_mutated_comp(connection: Type[connection], stim_id: int):
    """
    Return the component a delta mutated (parent_hypothesized_comps, in the parent's numbering)
    as a tuple of ints, or None if unknown. Falls back to the old table/column on un-migrated DBs.
    """
    table = _hypothesized_comp_table(connection)
    col = "parent_hypothesized_comps" if table == "HypothesizedComp" else "parent_comps_preserved"
    connection.execute(f"SELECT {col} FROM {table} WHERE stim_id = %s", (stim_id,))
    val = connection.fetch_one()
    if val is None or str(val).strip() == "":
        return None
    return tuple(int(x) for x in str(val).split(","))


def _write_hypothesized_comp_instruction(connection: Type[connection], *, stim_id: int,
                                         parent_id: int, comps: List[int] = None) -> None:
    """
    Instruct the Java side which component a delta should mutate, by pre-populating the delta's own
    HypothesizedComp row. The Java side reads parent_hypothesized_comps:
      - comps given  -> EXPLOIT: mutate exactly those components;
      - comps None   -> EXPLORE: row present but no component, so Java mutates a random component
                        different from the predicted one.
    (No row at all means PREDICT - the default - which this function never writes.)

    hypothesized_comp is left empty and filled in by Java once the delta is generated. Creates the
    table if needed, since Python may run before the Java generator creates it on a new experiment.
    """
    connection.execute(
        "CREATE TABLE IF NOT EXISTS HypothesizedComp ("
        "stim_id BIGINT PRIMARY KEY, "
        "hypothesized_comp VARCHAR(255) NOT NULL, "
        "parent_id BIGINT, "
        "parent_hypothesized_comps VARCHAR(255))")
    comps_str = "" if comps is None else ",".join(str(c) for c in comps)
    connection.execute(
        "INSERT INTO HypothesizedComp (stim_id, hypothesized_comp, parent_id, parent_hypothesized_comps) "
        "VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE hypothesized_comp = VALUES(hypothesized_comp), "
        "parent_id = VALUES(parent_id), parent_hypothesized_comps = VALUES(parent_hypothesized_comps)",
        (stim_id, "", parent_id, comps_str))

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
                 min_magnitude: float = 0.3, max_magnitude: float = 0.8):
        self.num_deltas_per_variant = num_deltas_per_variant
        self.delta_resp_ratio_threshold = delta_resp_ratio_threshold
        self.max_attempts_per_variant_multiplier = max_attempts_per_variant_multiplier
        self.conn = conn
        # Mutation magnitude for deltas is decided here (Python) rather than on the Java side,
        # mirroring how the rest of the GA assigns magnitudes. Drawn uniformly from
        # [min_magnitude, max_magnitude]. Discreteness is still chosen randomly on the Java side.
        self.min_magnitude = min_magnitude
        self.max_magnitude = max_magnitude

    def assign_mutation_magnitude(self) -> float:
        return random.uniform(self.min_magnitude, self.max_magnitude)

    def _mutated_comp_by_delta(self, deltas: List[Stimulus]) -> Dict[int, tuple]:
        """Map each responded delta's id to the component it mutated (a tuple of ints)."""
        comp_by_id: Dict[int, tuple] = {}
        for delta in deltas:
            if delta.response_rate is None:
                continue
            comp = _read_mutated_comp(self.conn, delta.id)
            if comp is not None:
                comp_by_id[delta.id] = comp
        return comp_by_id

    def run(self, lineages: List[Lineage], gen_id: int):
        #identify eligible stimuli (variants)
        # regimes = [l.current_regime_index for l in lineages]
        # if max(regimes) < 3:
        #     return
        variant_stimuli : List[Stimulus] = []
        lineages_for_stim_id = {}
        for lineage in lineages:
            for stim in lineage.stimuli:
                if stim.mutation_type == StimType.REGIME_ESTIM_VARIANTS.value:
                    if stim.response_rate is not None:
                        variant_stimuli.append(stim)
                        lineages_for_stim_id[stim.id] = lineage
        if len(variant_stimuli) == 0:
            return
        #filter out via response rate
        max_response_stim = max(variant_stimuli, key=lambda s: s.response_rate)
        threshold = max_response_stim.response_rate * 0.6

        past_threshold_stim: List[Stimulus] = []
        for s in variant_stimuli:
            if s.response_rate >= threshold:
                past_threshold_stim.append(s)

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
        # Predict phase lasts this many responded attempts (the "num_pairs * max_try" threshold);
        # the same budget caps how long we exploit a single component before giving up on it.
        budget = self.max_attempts_per_variant_multiplier * self.num_deltas_per_variant
        predict_attempts = budget
        eligible_stimuli : List[Stimulus] = []
        # variant_id -> instruction for its new deltas: None = predict (no row written),
        # ('EXPLORE', None) = let Java pick a random different comp, ('EXPLOIT', comp) = mutate comp.
        instruction_for_variant: Dict[int, tuple] = {}
        for candidate_parent in past_threshold_stim:
            eligible_deltas = eligible_deltas_for_variants.get(candidate_parent.id, [])
            all_deltas = deltas_for_variants.get(candidate_parent.id, [])

            # Group deltas by the component they actually mutated, so noise on the wrong component
            # is tracked separately from progress on the real driver.
            comp_by_id = self._mutated_comp_by_delta(all_deltas)
            responded_by_comp: Dict[tuple, int] = {}
            for comp in comp_by_id.values():
                responded_by_comp[comp] = responded_by_comp.get(comp, 0) + 1
            eligible_by_comp: Dict[tuple, int] = {}
            for delta in eligible_deltas:
                comp = comp_by_id.get(delta.id)
                if comp is not None:
                    eligible_by_comp[comp] = eligible_by_comp.get(comp, 0) + 1

            # Done when a SINGLE component has enough threshold-passing deltas. A lone noise-driven
            # eligible on the wrong component must not, by itself, satisfy the requirement.
            if max(eligible_by_comp.values(), default=0) >= self.num_deltas_per_variant:
                continue

            num_responded = len([d for d in all_deltas if d.response_rate is not None])
            num_in_flight = len(all_deltas) - num_responded

            # Decide the phase for this variant's new deltas.
            instruction = None  # predict: mutate the predicted comp (no row written)
            target_progress = max(eligible_by_comp.values(), default=0)  # predicted comp during predict
            if num_responded >= predict_attempts:
                # The predicted comp hasn't produced enough threshold-passing deltas. Exploit the
                # best component that (a) has a threshold-passing delta and (b) has not already been
                # tried up to `budget` times without reaching the target - such a component is
                # treated as a noise fluke and dropped, sending us back to exploration.
                exploit_comp = None
                eligible_with_comp = [(d.response_rate, comp_by_id[d.id]) for d in eligible_deltas
                                      if d.response_rate is not None and d.id in comp_by_id]
                for resp_rate, comp in sorted(eligible_with_comp, key=lambda x: x[0]):
                    if responded_by_comp.get(comp, 0) < budget:
                        exploit_comp = comp
                        break
                if exploit_comp is not None:
                    instruction = ('EXPLOIT', list(exploit_comp))
                    target_progress = eligible_by_comp.get(exploit_comp, 0)
                else:
                    instruction = ('EXPLORE', None)
                    target_progress = 0

            # Don't double-make: count progress toward the target component plus deltas in flight.
            number_of_deltas_to_make = self.num_deltas_per_variant - target_progress - num_in_flight
            if number_of_deltas_to_make <= 0:
                continue

            instruction_for_variant[candidate_parent.id] = instruction
            for i in range(number_of_deltas_to_make):
                eligible_stimuli.append(candidate_parent)


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

            # Pre-populate the delta's HypothesizedComp row to drive the predict/explore/exploit
            # progression. Predict (instruction None) writes nothing: Java mutates the predicted comp.
            instruction = instruction_for_variant.get(candidate_parent.id)
            if instruction is not None:
                regime, comp = instruction
                _write_hypothesized_comp_instruction(
                    self.conn, stim_id=new_stimulus.id, parent_id=candidate_parent.id,
                    comps=comp if regime == 'EXPLOIT' else None)

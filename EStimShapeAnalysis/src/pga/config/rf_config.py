from __future__ import annotations

import random
from typing import List, Protocol

import xmltodict
from clat.util.connection import Connection
from scipy.stats import stats

from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase, MutationMagnitudeAssigner, Lineage, Stimulus, ParentSelector, MutationAssigner, \
    RegimeTransitioner
from src.pga.regime_three import LeafingPhaseParentSelector, LeafingPhaseMutationAssigner, \
    LeafingPhaseMutationMagnitudeAssigner, LeafingPhaseTransitioner


class ZoomSetHandler(Protocol):
    conn: Connection

    def __init__(self, *, conn: Connection):
        self.conn = conn

    def is_empty_set(self, stimulus: Stimulus) -> bool:
        query = "SELECT COUNT(*) FROM ZoomingPhaseSets WHERE stim_id = %s"
        self.conn.execute(query, (stimulus.stim_id,))
        count = self.conn.fetch_one()
        return count == 0

    def is_partial_set(self, stimulus: Stimulus) -> bool:
        total_components_needed = self._get_num_comps_in(stimulus)
        query = "SELECT COUNT(*) FROM ZoomingPhaseSets WHERE stim_id = %s"
        self.conn.execute(query, (stimulus.stim_id,))
        count = self.conn.fetch_one()
        return 0 < count < total_components_needed

    def is_full_set(self, stimulus: Stimulus) -> bool:
        total_components_needed = self._get_num_comps_in(stimulus)
        query = "SELECT COUNT(*) FROM ZoomingPhaseSets WHERE stim_id = %s"
        self.conn.execute(query, (stimulus.stim_id,))
        count = self.conn.fetch_one()
        return count == total_components_needed

    def get_how_many_stimuli_needed_to_make_full_set(self, stimulus: Stimulus) -> int:
        total_components_needed = self._get_num_comps_in(stimulus)
        query = "SELECT COUNT(*) FROM ZoomingPhaseSets WHERE stim_id = %s"
        self.conn.execute(query, (stimulus.stim_id,))
        count = self.conn.fetch_one()
        return total_components_needed - count

    def get_next_stim_to_zoom(self, parent: Stimulus) -> int:
        # Find the remaining components left zoom
        total_comps = self._get_num_comps_in(parent)
        comp_ids = set(range(1, total_comps + 1))

        query = "SELECT comp_id FROM ZoomingPhaseSets WHERE stim_id = %s"
        self.conn.execute(query, (parent.id,))
        existing_comps = {row[0] for row in self.conn.fetch_all()}
        remaining_comps = list(comp_ids - existing_comps)

        if not remaining_comps:
            raise ValueError("No remaining components to choose from.")

        # Choose a random component to zone and write that we've tested this in the database
        chosen_comp_id = random.choice(remaining_comps)

        insert_query = "INSERT INTO ZoomingPhaseSets (stim_id, comp_id) VALUES (%s, %s)"
        self.conn.execute(insert_query, (parent.id, chosen_comp_id))

        return chosen_comp_id

    def _get_num_comps_in(self, stimulus: Stimulus) -> int:
        query = "SELECT data FROM StimSpec WHERE id=%s"
        self.conn.execute(query, (stimulus.id,))
        data = self.conn.fetch_one()
        data_dict = xmltodict.parse(data)
        n_comp = data_dict["AllenMStickData"]["analysisMStickSpec"]["mAxis"]["nComponent"]
        return int(n_comp)

    def is_zoomed_already(self, stimulus: Stimulus) -> bool:
        query = "SELECT data FROM StimSpec WHERE id=%s"
        self.conn.execute(query, (stimulus.id,))
        data = self.conn.fetch_one()
        data_dict = xmltodict.parse(data)
        rf_strategy = data_dict["AllenMStickData"]["rfStrategy"]
        if rf_strategy == "PARTIALLY_INSIDE":
            return True
        elif rf_strategy == "COMPLETELY_INSIDE":
            return False
        else:
            raise ValueError(f"Unknown RF strategy: {rf_strategy}")


class ZoomingPhaseTransitioner(RegimeTransitioner):
    zoom_set_handler: ZoomSetHandler
    percentage_full_set_threshold: float
    parent_selector: ZoomingPhaseParentSelector

    total_num_eligible: int
    num_full_sets: int
    num_partial_sets: int

    def __init__(self, *, zoom_set_handler: ZoomSetHandler, percentage_full_set_threshold: float,
                 parent_selector: ZoomingPhaseParentSelector):
        self.zoom_set_handler = zoom_set_handler
        self.percentage_full_set_threshold = percentage_full_set_threshold
        self.parent_selector = parent_selector

    def should_transition(self, lineage: Lineage):
        # Get all eligible stimuli for zooming
        eligible_stimuli = self.parent_selector.fetch_significantly_above_spontaneous_stimuli(lineage)
        self.parent_selector.filter_out_already_zoomed(eligible_stimuli)
        self.total_num_eligible = len(eligible_stimuli)

        # Check how many of these eligible stimuli have full set of zooming components
        self.num_full_sets = 0
        self.num_partial_sets = 0
        for stim in eligible_stimuli:
            if self.zoom_set_handler.is_full_set(stim):
                self.num_full_sets += 1
            elif self.zoom_set_handler.is_partial_set(stim):
                self.num_partial_sets += 1

        # If the percentage of stimuli with full sets is greater than the threshold, transition
        return self.num_full_sets / self.total_num_eligible >= self.percentage_full_set_threshold

    def get_transition_data(self, lineage):

        return f"Total number eligible for zooming: {self.total_num_eligible}, " \
               f"Number of full sets: {self.num_full_sets}, " \
               f"Number of partial sets: {self.num_partial_sets}"


class ZoomingPhaseParentSelector(ParentSelector):
    spontaneous_firing_rate: float
    significance_level: float
    zoom_set_handler: ZoomSetHandler

    def __init__(self, *, spontaneous_firing_rate: float, significance_level: float, zoom_set_handler: ZoomSetHandler):
        self.spontaneous_firing_rate = spontaneous_firing_rate
        self.significance_level = significance_level
        self.zoom_set_handler = zoom_set_handler

    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        potential_parents = self.fetch_significantly_above_spontaneous_stimuli(lineage)
        self.filter_out_already_zoomed(potential_parents)

        potential_parents_by_priority = self._prioritize_potential_parents(potential_parents)

        parents = self._choose_from_potential_parents(batch_size, potential_parents_by_priority)

        return parents

    def fetch_significantly_above_spontaneous_stimuli(self, lineage):
        # Look at all stimuli above spontaneous firing rate
        # Perform a one-sample t-test to determine whether the firing rate is significantly different from the spontaneous firing rate.
        stimuli_above_significance = []
        for stimulus in lineage.stimuli:
            t_stat, p_value = stats.ttest_1samp(stimulus.response_vector, self.spontaneous_firing_rate,
                                                alternative="greater")
            if p_value < self.significance_level:
                stimuli_above_significance.append(stimulus)
        return stimuli_above_significance

    def filter_out_already_zoomed(self, stimuli_above_significance):
        for stimulus in stimuli_above_significance:
            if self.zoom_set_handler.is_zoomed_already(stimulus):
                stimuli_above_significance.remove(stimulus)

    def _prioritize_potential_parents(self, potential_parents):
        empty_sets, partial_sets = (
            self._extract_empty_and_partial_sets(potential_parents))
        parents_by_priority = self._combine_to_prioritized_list(empty_sets, partial_sets)
        return parents_by_priority

    def _extract_empty_and_partial_sets(self, stimuli_above_significance):
        """
        Extracts separate lists of stimuli depending on whether they are empty or partial sets
        empty: no components for this stim_id have been zoomed yet
        partial: some components for this stim_id have been zoomed, but not all
        """
        no_sets = []
        partial_sets = []
        for stimulus in stimuli_above_significance:
            if self.zoom_set_handler.is_empty_set(stimulus):
                no_sets.append(stimulus)
            elif self.zoom_set_handler.is_partial_set(stimulus):
                partial_sets.append(stimulus)
        return no_sets, partial_sets

    def _combine_to_prioritized_list(self, no_sets, partial_sets):
        # Priortize each set by response rate
        no_sets.sort(key=lambda stim: stim.response_rate, reverse=True)
        partial_sets.sort(key=lambda stim: stim.response_rate, reverse=True)
        # Prioritize partial sets and then no sets
        parents_by_priority: List[Stimulus] = []
        parents_by_priority.extend(partial_sets)
        parents_by_priority.extend(no_sets)
        return parents_by_priority

    def _choose_from_potential_parents(self, batch_size, parents_by_priority):
        # Generate actual list of chosen parents.
        # Loop through the parents by priority, adding the number of stimuli needed to make a full set
        # Stop if we would add more than the batch size

        num_stim_remaining = batch_size
        parents = []
        while num_stim_remaining > 0:
            if len(parents_by_priority) == 0:
                print("No more parents to add")
                break
            parent = parents_by_priority.pop(0)
            num_to_add: int = self.zoom_set_handler.get_how_many_stimuli_needed_to_make_full_set(parent)
            if num_to_add > num_stim_remaining:
                num_to_add = num_stim_remaining
            parents.extend([parent] * num_to_add)
            num_stim_remaining -= num_to_add
        return parents


class ZoomingPhaseMutationAssigner(MutationAssigner):
    zoom_set_handler: ZoomSetHandler

    def __init__(self, *, zoom_set_handler: ZoomSetHandler):
        self.zoom_set_handler = zoom_set_handler

    def assign_mutation(self, lineage: Lineage, parent: Stimulus) -> str:
        stim_id = self.zoom_set_handler.get_next_stim_to_zoom(parent)
        return f"Zooming_{stim_id}"


class RFGeneticAlgorithmConfig(GeneticAlgorithmConfig):
    database = "allen_estimshape_ga_dev_240207"

    def make_phases(self):
        return [self.seeding_phase(),
                self.zooming_phase(),
                self.growing_phase(),
                self.leafing_phase()]

    def zooming_phase(self):
        return Phase(self.zooming_phase_parent_selector(),
                     self.zooming_phase_mutation_assigner(),
                     self.zooming_phase_mutation_magnitude_assigner(),
                     self.zooming_phase_transitioner())

    def zooming_phase_mutation_magnitude_assigner(self):
        return ZoomingPhaseMutationMagnitudeAssigner()

    def zooming_phase_parent_selector(self):
        return ZoomingPhaseParentSelector()


class ZoomingPhaseMutationMagnitudeAssigner(MutationMagnitudeAssigner):
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus):
        return None

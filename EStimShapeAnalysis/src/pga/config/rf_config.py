import random
from typing import List, Protocol

import xmltodict
from clat.util.connection import Connection
from scipy.stats import stats

from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase, MutationMagnitudeAssigner, Lineage, Stimulus, ParentSelector, MutationAssigner
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


class ZoomingPhaseMutationAssigner(MutationAssigner):
    zoom_set_handler: ZoomSetHandler

    def __init__(self, *, zoom_set_handler: ZoomSetHandler):
        self.zoom_set_handler = zoom_set_handler

    def assign_mutation(self, lineage: Lineage, parent: Stimulus) -> str:
        stim_id = self.zoom_set_handler.get_next_stim_to_zoom(parent)
        return f"Zooming_{stim_id}"


class ZoomingPhaseParentSelector(ParentSelector):
    spontaneous_firing_rate: float
    significance_level: float
    zoom_set_handler: ZoomSetHandler

    def __init__(self, *, spontaneous_firing_rate: float, significance_level: float, zoom_set_handler: ZoomSetHandler):
        self.spontaneous_firing_rate = spontaneous_firing_rate
        self.significance_level = significance_level
        self.zoom_set_handler = zoom_set_handler

    def select_parents(self, lineage: Lineage, batch_size: int) -> list[Stimulus]:
        # Look at all stimuli above spontaneous firing rate
        # Perform a one-sample t-test to determine whether the firing rate is significantly different from the spontaneous firing rate.
        stimuli_above_significance = []
        for stimulus in lineage.stimuli:
            t_stat, p_value = stats.ttest_1samp(stimulus.response_vector, self.spontaneous_firing_rate,
                                                alternative="greater")
            if p_value < self.significance_level:
                stimuli_above_significance.append(stimulus)
        print([stimulus.response_rate for stimulus in stimuli_above_significance])

        # See if any have no zoom set, partial set, or full set
        no_sets = []
        partial_sets = []
        for stimulus in stimuli_above_significance:
            if self.zoom_set_handler.is_empty_set(stimulus):
                no_sets.append(stimulus)
            elif self.zoom_set_handler.is_partial_set(stimulus):
                partial_sets.append(stimulus)
        print(f"no sets: {[stimulus.response_rate for stimulus in no_sets]}")
        print(f"partial sets: {[stimulus.response_rate for stimulus in partial_sets]}")

        # Priortize each set by response rate
        no_sets.sort(key=lambda stim: stim.response_rate, reverse=True)
        partial_sets.sort(key=lambda stim: stim.response_rate, reverse=True)

        # Prioritize partial sets and then no sets
        parents_by_priority: List[Stimulus] = []
        parents_by_priority.extend(partial_sets)
        parents_by_priority.extend(no_sets)
        print(f"parents by priority: {[stimulus.response_rate for stimulus in parents_by_priority]}")

        # Generate actual list of Partial Stimuli.
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

        print(f"parents: {[stimulus.response_rate for stimulus in parents]}")

        return parents


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

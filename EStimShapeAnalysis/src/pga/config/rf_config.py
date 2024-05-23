from typing import List

from scipy.stats import stats

from src.pga.config.canopy_config import GeneticAlgorithmConfig
from src.pga.ga_classes import Phase, MutationMagnitudeAssigner, Lineage, Stimulus, ParentSelector, MutationAssigner
from src.pga.regime_three import LeafingPhaseParentSelector, LeafingPhaseMutationAssigner, \
    LeafingPhaseMutationMagnitudeAssigner, LeafingPhaseTransitioner


class ZoomSetHandler:

    def is_no_set(self, stimulus: Stimulus) -> bool:
        pass

    def is_partial_set(self, stimulus: Stimulus) -> bool:
        pass

    def is_full_set(self, stimulus: Stimulus) -> bool:
        pass

    def get_how_many_stimuli_needed_to_make_full_set(self, stimulus: Stimulus) -> int:
        pass

    def get_next_stim_to_zoom(self, parent) -> int:
        pass


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
            if self.zoom_set_handler.is_no_set(stimulus):
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

import numpy as np

from pga.stim_types import StimType
from src.pga.ga_classes import Stimulus, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, \
    RegimeTransitioner, Lineage
from scipy import stats


class SeedingPhaseParentSelector(ParentSelector):
    def select_parents(self, lineage, batch_size):
        # In Regime Zero, there are no parents.
        return [Stimulus(0, "None", parent_id=0)] * batch_size


class SeedingPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus):
        # In Regime Zero, all stimuli are assigned the "RegimeZero" mutation.
        return StimType.REGIME_ZERO.value


class SeedingPhaseMutationMagnitudeAssigner(MutationMagnitudeAssigner):
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus):
        # In Regime Zero, mutation magnitude is meaningless.
        return None


class SeedingPhaseTransitioner(RegimeTransitioner):
    def __init__(self, spontaneous_firing_rate, significance_level):
        self.spontaneous_firing_rate = spontaneous_firing_rate
        self.significance_level = significance_level
        self.t_stat = None
        self.p_value = None

    def should_transition(self, lineage):
        # Perform a one-sample t-test to determine whether the firing rate is significantly different from the spontaneous firing rate.
        firing_rates = lineage.stimuli[0].response_vector
        self.t_stat, self.p_value = stats.ttest_1samp(firing_rates, self.spontaneous_firing_rate, alternative="greater")
        return self.p_value < self.significance_level

    def get_transition_data(self, lineage):
        data = {"p_value": self.p_value, "t_stat": self.t_stat}
        return str(data)



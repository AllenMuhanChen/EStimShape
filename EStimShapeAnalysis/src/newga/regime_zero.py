from src.newga.ga_classes import Stimulus, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, \
    RegimeTransitioner, Lineage
from scipy import stats


class RegimeZeroParentSelector(ParentSelector):
    def select_parents(self, lineage, batch_size):
        # In Regime Zero, there are no parents.
        return [None] * batch_size


class RegimeZeroMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage):
        # In Regime Zero, all stimuli are assigned the "RegimeZero" mutation.
        return "RegimeZero"


class RegimeZeroMutationMagnitudeAssigner(MutationMagnitudeAssigner):
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus):
        # In Regime Zero, mutation magnitude is meaningless.
        return None


class RegimeZeroTransitioner(RegimeTransitioner):
    def __init__(self, spontaneous_firing_rate, significance_level):
        self.spontaneous_firing_rate = spontaneous_firing_rate
        self.significance_level = significance_level

    def should_transition(self, lineage):
        # Perform a one-sample t-test to determine whether the firing rate is significantly different from the spontaneous firing rate.
        firing_rates = lineage.stimuli[0].response_vector
        t_stat, p_value = stats.ttest_1samp(firing_rates, self.spontaneous_firing_rate)
        return p_value < self.significance_level

import numpy as np

from newga.regime_type import RegimeType
from src.newga.ga_classes import ParentSelector, MutationAssigner, RegimeTransitioner, MutationMagnitudeAssigner, \
    Lineage, Stimulus


class RegimeTwoParentSelector(ParentSelector):
    """
    Samples from the top x stimuli that pass a threshold across a lineage.
    """

    def __init__(self, percentage_of_max_threshold, x):
        self.percentage_of_max_threshold = percentage_of_max_threshold
        self.x = x

    def select_parents(self, lineage, batch_size):
        # Select the top x stimuli from the lineage based on their response rate.
        top_stimuli = sorted(lineage.stimuli, key=lambda s: s.response_rate, reverse=True)[:self.x]
        # Filter out any stimuli that fall below a certain percentage of the max response rate.
        max_response_rate = top_stimuli[0].response_rate
        threshold = max_response_rate * self.percentage_of_max_threshold  # Adjust this value as necessary.
        qualified_stimuli = [s for s in top_stimuli if s.response_rate >= threshold]
        # Sample with replacement from the stimuli that passed the threshold.
        return np.random.choice(qualified_stimuli, size=batch_size, replace=True).tolist()


class RegimeTwoMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage):
        return RegimeType.REGIME_TWO.value


class RegimeTwoMutationMagnitudeAssigner(MutationMagnitudeAssigner):

    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus):
        return None


class RegimeTwoTransitioner(RegimeTransitioner):
    def __init__(self, pair_threshold_high, pair_threshold_low):
        self.pair_threshold = {'high': pair_threshold_high, 'low': pair_threshold_low}

    def should_transition(self, lineage: Lineage):
        self.pair_counts = {'high': 0, 'low': 0}
        # Update the counts for high- and low-response pairs.
        for stimulus in lineage.stimuli:
            if stimulus.parent_id is not None and stimulus.mutation_type == RegimeType.REGIME_TWO.value:
                ratio = min(stimulus.response_rate / lineage.get_parent_of(stimulus).response_rate, 1)
                if ratio > 0.75:
                    self.pair_counts['high'] += 1
                elif ratio < 0.25:
                    self.pair_counts['low'] += 1
        # Check if both counts have reached the threshold.
        return self.pair_counts['high'] >= self.pair_threshold['high'] and self.pair_counts['low'] >= \
            self.pair_threshold['low']

    def get_transition_data(self, lineage):
        data = self.pair_counts
        return str(data)



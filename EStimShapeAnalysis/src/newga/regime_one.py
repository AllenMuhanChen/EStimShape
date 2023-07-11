# regime_one.py
from typing import Callable, List

from src.newga.ga_classes import Stimulus, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, \
    RegimeTransitioner, Lineage
import numpy as np

from src.util.connection import Connection


class RankOrderedDistribution:
    def __init__(self, stimuli: [Stimulus], proportions: [float]):
        self.stimuli = sorted(stimuli, key=lambda s: s.response_rate, reverse=True)
        self.proportions = proportions
        self._generate_bins()

    def _generate_bins(self):
        bins: [[Stimulus]]
        # Determine the size of each bin based on the total number of stimuli.
        total_stimuli = len(self.stimuli)
        bin_sizes = [int(total_stimuli * proportion) for proportion in self.proportions]

        # Ensure the sum of bin_sizes equals total_stimuli.
        # This handles potential rounding errors in the calculation of bin_sizes.
        bin_sizes[-1] += total_stimuli - sum(bin_sizes)

        # Split the stimuli into bins.
        self.bins = []
        start = 0
        for size in bin_sizes:
            self.bins.append(self.stimuli[start:start + size])
            start += size

    def sample_from_bin(self, bin_index, num_samples) -> [Stimulus]:
        # Use the corresponding sample size for this bin.
        random = np.random.choice(self.bins[bin_index], num_samples)
        return list(random)

    def sample(self, bin_sample_sizes: [int]) -> [Stimulus]:
        # Sample from all bins and concatenate the results.
        return [self.sample_from_bin(i, bin_sample_sizes[i]) for i in range(len(self.bins))]


class RegimeOneParentSelector(ParentSelector):
    """
    Samples stimuli from the rank-ordered distribution across all lineages.
    When sampling stimuli for each lineage, it checks if any of its stimuli are in the sample
    and adds them to the list of parents.
    """

    def __init__(self, get_all_stimuli_func: Callable[[], List[Stimulus]], proportions: [float], bin_sample_sizes: [int]) -> None:
        self.get_all_stimuli_func = get_all_stimuli_func
        self.proportions = proportions
        self.bin_sample_sizes = bin_sample_sizes
        self.rank_ordered_distribution = RankOrderedDistribution(self.get_all_stimuli_func(), self.proportions)
        self.sampled_stimuli_from_all_lineages = self.rank_ordered_distribution.sample(bin_sample_sizes)

    def select_parents(self, lineage, batch_size):
        # Identify the stimuli from the current lineage in the rank-ordered distribution
        parents = []
        for bin in self.sampled_stimuli_from_all_lineages:
            for stimulus in bin:
                if any([stimulus == stimulus_from_lineage for stimulus_from_lineage in lineage.stimuli]):
                    parents.append(stimulus)
        return parents


class RegimeOneMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage):
        return "RegimeOne"


# regime_one.py

class RegimeOneMutationMagnitudeAssigner(MutationMagnitudeAssigner):
    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus):
        # Calculate the response rates of the stimuli and normalize them to the range [0, 1].
        response_rates = np.array([s.response_rate for s in lineage.stimuli])
        normalized_response_rates = (response_rates - np.min(response_rates)) / (
                np.max(response_rates) - np.min(response_rates))

        # Assign mutation magnitudes probabilistically based on normalized response rates.
        # We subtract the normalized response rates from 1 so that higher ranked stimuli have higher probabilities of receiving smaller mutations.
        probabilities = 1 - normalized_response_rates
        probabilities /= probabilities.sum()  # Ensure probabilities sum to 1
        return np.random.choice(np.linspace(0, 1, len(lineage.stimuli)), p=probabilities)


class RegimeOneTransitioner(RegimeTransitioner):
    def __init__(self, convergence_threshold):
        self.convergence_threshold = convergence_threshold
        self.previous_peak_response = None

    @staticmethod
    def _calculate_peak_response(lineage):
        # Calculate the peak response for the current batch of stimuli as the average of the top 3 responses.
        top_responses = sorted([s.response_rate for s in lineage.stimuli], reverse=True)[:3]
        return np.mean(top_responses)

    def should_transition(self, lineage):
        current_peak_response = self._calculate_peak_response(lineage)

        if self.previous_peak_response is not None:
            # Calculate the change in the peak response.
            change = abs((current_peak_response - self.previous_peak_response) / self.previous_peak_response)

            # Transition to the next regime if the change is below the convergence threshold.
            if change < self.convergence_threshold:
                return True

        # Update the previous peak response for the next batch.
        self.previous_peak_response = current_peak_response

        return False

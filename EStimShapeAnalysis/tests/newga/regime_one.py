# regime_one.py

from src.newga.ga_classes import Stimulus, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, \
    RegimeTransitioner
import numpy as np


class RankOrderedDistribution:
    def __init__(self, stimuli, proportions):
        self.stimuli = sorted(stimuli, key=lambda s: s.response_rate, reverse=True)
        self.proportions = proportions
        self.bins = self._generate_bins()

    def _generate_bins(self):
        # Determine the size of each bin based on the total number of stimuli.
        total_stimuli = len(self.stimuli)
        bin_sizes = [int(total_stimuli * proportion) for proportion in self.proportions]

        # Ensure the sum of bin_sizes equals total_stimuli.
        # This handles potential rounding errors in the calculation of bin_sizes.
        bin_sizes[-1] += total_stimuli - sum(bin_sizes)

        # Split the stimuli into bins.
        bins = []
        start = 0
        for size in bin_sizes:
            bins.append(self.stimuli[start:start + size])
            start += size

        return bins

    def sample_from_bin(self, bin_index, size):
        return np.random.choice(self.bins[bin_index], size)

class RegimeOneParentSelector(ParentSelector):
    def rank_ordered_stimuli(self, stimuli):
        return RankOrderedDistribution(stimuli)

    def select_parents(self, stimuli, batch_size):
        # Create a RankOrderedDistribution from all stimuli across lineages
        rank_ordered_distribution = self.rank_ordered_stimuli(stimuli)

        # Identify the stimuli from the current lineage in the rank-ordered distribution
        parents = []
        for bin_stimuli in rank_ordered_distribution.bins:
            for stimulus in bin_stimuli:
                if stimulus in stimuli:
                    parents.append(stimulus)
                if len(parents) == batch_size:
                    return parents
        return parents


class RegimeOneMutationAssigner(MutationAssigner):
    def assign_mutation(self):
        return "RegimeOne"


class RegimeOneMutationMagnitudeAssigner(MutationMagnitudeAssigner):
    def assign_mutation_magnitude(self, stimuli):
        # Calculate the response rates of the stimuli and normalize them to the range [0, 1].
        response_rates = np.array([s.response_rate for s in stimuli])
        normalized_response_rates = (response_rates - np.min(response_rates)) / (
                    np.max(response_rates) - np.min(response_rates))

        # Assign mutation magnitudes inversely proportional to normalized response rates.
        # We subtract the normalized response rates from 1 so that higher ranked stimuli receive smaller mutations.
        return 1 - normalized_response_rates


class RegimeOneTransitioner(RegimeTransitioner):
    def __init__(self, convergence_threshold):
        self.convergence_threshold = convergence_threshold
        self.previous_peak_response = None

    def _calculate_peak_response(self, stimuli):
        # Calculate the peak response for the current batch of stimuli as the average of the top 3 responses.
        top_responses = sorted([s.response_rate for s in stimuli], reverse=True)[:3]
        return np.mean(top_responses)

    def should_transition(self, stimuli):
        current_peak_response = self._calculate_peak_response(stimuli)

        if self.previous_peak_response is not None:
            # Calculate the change in the peak response.
            change = abs((current_peak_response - self.previous_peak_response) / self.previous_peak_response)

            # Transition to the next regime if the change is below the convergence threshold.
            if change < self.convergence_threshold:
                return True

        # Update the previous peak response for the next batch.
        self.previous_peak_response = current_peak_response

        return False

# regime_one.py
import math
from dataclasses import dataclass
from typing import Callable, List

from pga.response_processing import ResponseProcessor
from pga.multi_ga_db_util import MultiGaDbUtil
from pga.regime_type import RegimeType
from src.pga.ga_classes import Stimulus, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, \
    RegimeTransitioner, Lineage
import numpy as np

from clat.util.connection import Connection


class RankOrderedDistribution:
    def __init__(self, stimuli: [Stimulus], proportions: [float]):
        self.stimuli = sorted(stimuli, key=lambda s: s.response_rate)
        self.proportions = proportions
        self._generate_bins()

    def _generate_bins(self):
        total_stimuli = len(self.stimuli)

        bin_sizes = [0] * len(self.proportions)
        if total_stimuli < len(self.proportions):
            for i in range(total_stimuli):
                bin_sizes[-(i + 1)] = 1
        else:
            bin_sizes = [int(total_stimuli * proportion) for proportion in self.proportions]

        # Calculate the remainder and distribute it randomly between the bins.
        remainder = total_stimuli - sum(bin_sizes)
        if remainder > 0:
            random_indices = np.random.choice(len(self.proportions), remainder, p=self.proportions)
            for index in random_indices:
                bin_sizes[index] += 1

        # Split the stimuli into bins.
        self.bins = []
        start = 0
        for size in bin_sizes:
            self.bins.append(self.stimuli[start: start + size])
            start += size

    def sample_total_amount_across_bins(self, bin_sample_probabilities: [float], total: int) -> [Stimulus]:
        """
        You specify a total number of samples and the proportion of samples you want from each bin.
        This then samples the total number of samples from bins using the proportion
        as a PROBABILITY of sampling from that bin.

        So the proportion assigned is not absolute, it is just a probability.
        :param bin_sample_probabilities: relative likelihood of sampling from each bin
        :param total: total number of samples to take
        :return: list of samples
        """
        if len(bin_sample_probabilities) != len(self.bins):
            raise ValueError("The number of bin sample proportions must equal the number of bins.")

        # Remove the empty bins
        non_empty_bins = [bin for bin in self.bins if len(bin) > 0]
        non_empty_bin_sample_probabilities = [proportion for proportion, bin in zip(bin_sample_probabilities, self.bins)
                                              if
                                              len(bin) > 0]

        # Sample total amount
        samples = []

        # normalize bin_sample_proportions
        non_empty_bin_sample_probabilities = [proportion / sum(non_empty_bin_sample_probabilities) for proportion in
                                              non_empty_bin_sample_probabilities]

        # Sampling from the non-empty bins with replacement
        for i in range(total):
            bin_index = np.random.choice(len(non_empty_bins), p=non_empty_bin_sample_probabilities)
            samples.append(np.random.choice(non_empty_bins[bin_index]))
        return samples

    def sample_amount_per_bin(self, *, amount_per_bin: [int]) -> [Stimulus]:
        """
        Samples a specific amount from each bin. If a bin is empty, it adds the sample size to the next bin.
        :param amount_per_bin: the amount to sample from each bin
        :return: list of samples
        """
        if len(amount_per_bin) != len(self.bins):
            raise ValueError("The number of bin sample sizes must equal the number of bins.")
        # Sample from all bins and concatenate the results.
        samples = []
        for i, bin in enumerate(self.bins):
            # If the bin is empty, add the sample size to the next bin.
            if len(bin) == 0 and i < len(self.bins) and amount_per_bin[i] > 0:
                amount_per_bin[i + 1] += amount_per_bin[i]
            else:
                samples.append(self._sample_from_bin(i, amount_per_bin[i]))
        return samples

    def _sample_from_bin(self, bin_index, num_samples) -> [Stimulus]:
        # Use the corresponding sample size for this bin.
        random = np.random.choice(self.bins[bin_index], num_samples)
        return list(random)


class GrowingPhaseParentSelector(ParentSelector):
    """
    Samples stimuli from the rank-ordered distribution across all lineages.
    When sampling stimuli for each lineage, it checks if any of its stimuli are in the sample
    and adds them to the list of parents.
    """

    def __init__(self, get_all_stimuli_func: Callable[[], List[Stimulus]], proportions: [float],
                 bin_sample_proportions: [int]) -> None:
        self.get_all_stimuli_func = get_all_stimuli_func
        self.proportions = proportions
        self.bin_sample_sizes_proportions = bin_sample_proportions

    def distribute_samples_to_bins(self, total_sample_size: int) -> [int]:
        # if total_sample_size
        num_samples = [round(total_sample_size * proportion) for proportion in self.proportions]
        remainder = total_sample_size - sum(num_samples)
        if remainder > 0:
            random_indices = np.random.choice(len(self.proportions), remainder, p=self.proportions)
            for index in random_indices:
                num_samples[index] += 1
        return num_samples

    def select_parents(self, lineage, batch_size):
        rank_ordered_distribution = RankOrderedDistribution(lineage.stimuli, self.proportions)
        sampled_stimuli_from_all_lineages = rank_ordered_distribution.sample_total_amount_across_bins(
            bin_sample_probabilities=self.bin_sample_sizes_proportions, total=batch_size)

        # Identify the stimuli from the current lineage in the rank-ordered distribution
        parents = []
        for stimulus in sampled_stimuli_from_all_lineages:
            if any([stimulus == stimulus_from_lineage for stimulus_from_lineage in lineage.stimuli]):
                parents.append(stimulus)
        return parents


@dataclass(kw_only=True)
class GetAllStimuliFunc:
    db_util: MultiGaDbUtil
    ga_name: str
    response_processor: ResponseProcessor

    def __call__(self) -> List[Stimulus]:
        # Find out current experiment_id
        experiment_id = self.db_util.read_current_experiment_id(self.ga_name)

        # Find all lineage_ids with that id
        lineage_ids = self.db_util.read_lineage_ids_for_experiment_id(experiment_id)

        # Find all stim ids for those lineage_ids
        stim_ids = []
        for lineage_id in lineage_ids:
            stim_ids.extend(self.db_util.read_stim_ids_for_lineage(lineage_id))

        # Read StimGaInfoEntry for each stim_id
        def stim_id_to_stimulus(stim_id: int) -> Stimulus:
            stim_ga_info_entry = self.db_util.read_stim_ga_info_entry(stim_id)
            mutation_type = stim_ga_info_entry.stim_type
            response = stim_ga_info_entry.response
            response_vector = self.response_processor.fetch_response_vector_for(stim_id, ga_name=self.ga_name)
            return Stimulus(stim_id, mutation_type, response_vector=response_vector, driving_response=response)

        stimuli = []
        for stim_id in stim_ids:
            stimuli.append(stim_id_to_stimulus(stim_id))

        return stimuli


class GrowingPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus):
        return RegimeType.REGIME_ONE.value


# regime_one.py

class GrowingPhaseMutationMagnitudeAssigner(MutationMagnitudeAssigner):
    min_magnitude = 0.1
    max_magnitude = 0.5

    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus):
        # Calculate the response rates of the stimuli and normalize them to the range [0, 1].
        response_rates = np.array([s.response_rate for s in lineage.stimuli])
        normalized_response_rates = []
        for rate in response_rates:
            if max(response_rates) != 0:
                normalized_response_rates.append(rate / max(response_rates))
            else:
                normalized_response_rates.append(0)


        # Assign mutation magnitudes probabilistically based on normalized response rates.
        # We subtract the normalized response rates from 1.1 so that higher ranked stimuli have higher probabilities of receiving smaller mutations.
        if len(normalized_response_rates) > 1:
            scores = [1.1 - normalized_response_rate for normalized_response_rate in normalized_response_rates]
            probabilities = [s / sum(scores) for s in scores]  # Ensure probabilities sum to 1
            return np.random.choice(np.linspace(self.min_magnitude, self.max_magnitude, len(lineage.stimuli)),
                                p=probabilities)
        else:
            return np.random.uniform(self.min_magnitude, self.max_magnitude)


def calculate_peak_response(responses, across_n=3):
    # Ensure the list of responses is at least of length across_n, filling missing values with 0
    extended_responses = responses + [0] * (across_n - len(responses))

    # Calculate the peak response for the current batch of stimuli as the average of the top 3 responses.
    # It uses the extended list but still selects only the top 'across_n' responses, which now includes 0s if necessary.
    top_responses = sorted(extended_responses, reverse=True)[:across_n]
    return np.mean(top_responses)


class GrowingPhaseTransitioner(RegimeTransitioner):
    def __init__(self, convergence_threshold):
        self.convergence_threshold = convergence_threshold
        self.x = 4
        self.change = None
        self.peak_responses = None

    def should_transition(self, lineage):
        self.peak_responses = []
        self.change = None

        latest_gen_id = lineage.gen_id - 1
        generations_analyzed = 0
        gen_ids_to_analyze = []

        while generations_analyzed < self.x and latest_gen_id > 0:
            responses_in_generation = [s.response_rate for s in lineage.stimuli if s.gen_id == latest_gen_id]

            if len(responses_in_generation) > 0:
                gen_ids_to_analyze.append(latest_gen_id)
                generations_analyzed += 1

            latest_gen_id -= 1


        for gen_id in gen_ids_to_analyze:
            responses_up_to_and_including_generation = [s.response_rate for s in lineage.stimuli if s.gen_id <= gen_id]
            self.peak_responses.append(calculate_peak_response(responses_up_to_and_including_generation))

        if generations_analyzed < self.x:
            # Not enough valid generations to analyze
            return False

        self.change = abs((self.peak_responses[-1] - self.peak_responses[0]) / self.x)
        return self.convergence_threshold > self.change

    def get_transition_data(self, lineage):
        data = {"current_peak_response": self.peak_responses, "change": self.change}
        return str(data)

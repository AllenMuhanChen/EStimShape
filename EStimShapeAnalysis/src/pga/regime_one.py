# regime_one.py
from dataclasses import dataclass
from typing import Callable, List

import numpy as np

from src.pga.ga_classes import Stimulus, ParentSelector, MutationAssigner, MutationMagnitudeAssigner, \
    RegimeTransitioner, Lineage
from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.pga.response_processing import GAResponseProcessor
from src.pga.stim_types import StimType


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
    Samples stimuli from the rank-ordered distribution across its lineage.

    bin_proportions:  what percent of stimuli should be in each bin (i.e .5, .3, .2) for 3 bins means 50% in bin 1, 30% in bin 2, 20% in bin 3
    bin_sample_proportions: what percent of samples should be taken from each bin (i.e .5, .3, .2) for 3 bins means 50% of samples from bin 1, 30% from bin 2, 20% from bin 3
    """
    bin_sample_probabilities: [int]

    def __init__(self, proportions: [float], bin_sample_proportions: [int]) -> None:
        self.bin_proportions = proportions
        self.bin_sample_probabilities = bin_sample_proportions

    def select_parents(self, lineage, batch_size):
        rank_ordered_distribution = RankOrderedDistribution(lineage.stimuli, self.bin_proportions)
        sampled_stimuli_from_lineage = rank_ordered_distribution.sample_total_amount_across_bins(
            bin_sample_probabilities=self.bin_sample_probabilities, total=batch_size)

        parents = sampled_stimuli_from_lineage
        return parents


@dataclass(kw_only=True)
class GetAllStimuliFunc:
    db_util: MultiGaDbUtil
    ga_name: str
    response_processor: GAResponseProcessor

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
            response_vector = self.response_processor.fetch_response_vector_for_repetitions_of(stim_id,
                                                                                               ga_name=self.ga_name)
            return Stimulus(stim_id, mutation_type, response_vector=response_vector, response_rate=response)

        stimuli = []
        for stim_id in stim_ids:
            stimuli.append(stim_id_to_stimulus(stim_id))

        return stimuli


class GrowingPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage, parent: Stimulus) -> str:
        return StimType.REGIME_ONE.value


# regime_one.py
import numpy as np
from scipy.stats import truncnorm


class GrowingPhaseMutationMagnitudeAssigner(MutationMagnitudeAssigner):
    def __init__(self, std_dev=0.05, min_magnitude=0.05, max_magnitude=0.5):
        """
        Initialize with standard deviation for normal distribution and magnitude bounds.
        std_dev of 0.075 means:
        - ~68% of values will be within ±0.05 of the mean (within 0.1 range)
        - ~95% of values will be within ±0.10 of the mean (within 0.2 range)
        min_magnitude sets the absolute minimum mutation magnitude possible.
        max_magnitude sets the absolute maximum mutation magnitude possible.
        """
        self.std_dev = std_dev
        self.min_magnitude = min_magnitude
        self.max_magnitude = max_magnitude

    def get_truncated_normal(self, mean):
        """
        Returns a value from a truncated normal distribution between
        [min_magnitude, max_magnitude] with specified mean and class-defined
        standard deviation
        """
        # Ensure mean stays within reasonable bounds
        mean = np.clip(mean, self.min_magnitude, self.max_magnitude)

        # Calculate normalized bounds for truncated normal
        a_norm = (self.min_magnitude - mean) / self.std_dev
        b_norm = (self.max_magnitude - mean) / self.std_dev

        # Sample from truncated normal
        sample = truncnorm.rvs(
            a_norm,
            b_norm,
            loc=mean,
            scale=self.std_dev,
            size=1
        )[0]

        # Double-ensure bounds are respected
        return np.clip(sample, self.min_magnitude, self.max_magnitude)

    def assign_mutation_magnitude(self, lineage: Lineage, parent: Stimulus):
        """
        Assigns mutation magnitude by sampling from a truncated normal distribution
        centered at (1.1 - normalized_response_rate). Higher response rates lead to
        sampling from distributions centered closer to 0.1, resulting in smaller
        mutation magnitudes. All magnitudes are guaranteed to be between
        min_magnitude and max_magnitude.
        """
        # Normalize response rates, only considering positive responses
        response_rates = np.array([s.response_rate for s in lineage.stimuli if s.response_rate > 0])
        if len(response_rates) == 0 or max(response_rates) == 0:
            normalized_rate = 0
        else:
            parent_rate = parent.response_rate
            normalized_rate = parent_rate / max(response_rates)

        # Center distribution mean at (1.1 - normalized_rate), but ensure it doesn't
        # push the mean beyond max_magnitude
        mean = min(1 + self.min_magnitude - normalized_rate, self.max_magnitude)

        # Sample from truncated normal distribution between min_magnitude and max_magnitude
        return self.get_truncated_normal(mean)
def calculate_peak_response(responses, across_n=3):
    # Ensure the list of responses is at least of length across_n, filling missing values with 0
    # remove nones
    responses = [response for response in responses if response is not None]
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

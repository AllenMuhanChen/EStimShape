# regime_three.py
import math
from typing import Callable

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.stats import gaussian_kde

from pga.ga_classes import Lineage, Stimulus
from pga.regime_type import RegimeType
from src.pga.ga_classes import ParentSelector, MutationAssigner, RegimeTransitioner, MutationMagnitudeAssigner


class SmoothedSamplingFunction:
    def __init__(self, bandwidth):
        self.bandwidth = bandwidth

    def __call__(self, responses):
        kde = gaussian_kde(responses, bw_method=self.bandwidth)

        def sampling_func(x):
            result = kde(x)
            return result / np.max(result)  # normalize the result so that the maximum is 1

        return sampling_func


class LeafingPhaseParentSelector(ParentSelector):
    def __init__(self, weight_func: Callable[[float], float], bandwidth=0.15):
        self.weight_func = weight_func
        self.sampling_func = SmoothedSamplingFunction(bandwidth=bandwidth)

    def select_parents(self, lineage, batch_size):
        # Calculate the sampling function.
        responses = [s.response_rate for s in lineage.stimuli]
        if max(responses) - min(responses) == 0:
            normalized_responses = [0] * len(responses)
        normalized_responses = [response - min(responses) / (max(responses) - min(responses)) for response in responses]
        sampling_func = self.sampling_func(normalized_responses)

        # Calculate the fitness scores.
        fitness_scores = [self.weight_func(r) / sampling_func(r) for r in normalized_responses]

        # Normalize the fitness scores.
        fitness_scores /= np.sum(fitness_scores)
        fitness_scores = np.squeeze(fitness_scores)

        # Select parents probabilistically based on fitness scores.
        return np.random.choice(lineage.stimuli, size=batch_size, p=fitness_scores, replace=True)


class LeafingPhaseMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage):
        return RegimeType.REGIME_THREE.value


class LeafingPhaseMutationMagnitudeAssigner(MutationMagnitudeAssigner):

    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        return 0.1


class LeafingPhaseTransitioner(RegimeTransitioner):
    def __init__(self, under_sampling_threshold, bandwidth=0.15):
        self.under_sampling_threshold = under_sampling_threshold
        self.sampling_func_calculator = SmoothedSamplingFunction(bandwidth=bandwidth)

    def should_transition(self, lineage):
        # Calculate the sampling function.
        responses = [s.response_rate for s in lineage.stimuli]
        sampling_func = self.sampling_func_calculator(responses)

        # Check if there are under-sampled regions.
        x = np.linspace(min(responses), max(responses), 1000)
        y = sampling_func(x)
        return not np.any(y < self.under_sampling_threshold)

    def get_transition_data(self, lineage):
        return "Unimplemented"


class HighEndSigmoid:
    def __init__(self, steepness=15.0, offset=0.5):
        """
        :param steepness: Controls the steepness of the curve.
        :param offset: Shifts the curve to favor the higher end.
        """
        self.steepness = steepness
        self.offset = offset

    def __call__(self, x: float) -> float:
        """
        Apply the sigmoid function.

        :param x: A value between 0 and 1.
        :return: A value between 0 and 1, favoring the higher end.
        """
        # Apply the sigmoid function with the given steepness and offset
        return 1 / (1 + math.exp(-self.steepness * (x - self.offset)))

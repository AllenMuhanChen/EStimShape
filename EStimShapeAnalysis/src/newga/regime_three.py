# regime_three.py
from typing import Callable

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.stats import gaussian_kde

from newga.ga_classes import Lineage, Stimulus
from src.newga.ga_classes import ParentSelector, MutationAssigner, RegimeTransitioner, MutationMagnitudeAssigner


class SmoothedSamplingFunction:
    def __init__(self, bandwidth):
        self.bandwidth = bandwidth

    def __call__(self, responses):
        kde = gaussian_kde(responses, bw_method=self.bandwidth)

        def sampling_func(x):
            result = kde(x)
            return result / np.max(result)  # normalize the result so that the maximum is 1

        return sampling_func


class RegimeThreeParentSelector(ParentSelector):
    def __init__(self, weight_func: Callable[[float], float], bandwidth=0.15):
        self.weight_func = weight_func
        self.sampling_func = SmoothedSamplingFunction(bandwidth=bandwidth)

    def select_parents(self, lineage, batch_size):
        # Calculate the sampling function.
        responses = [s.response_rate for s in lineage.stimuli]
        sampling_func = self.sampling_func(responses)

        # Calculate the fitness scores.
        fitness_scores = [self.weight_func(r) / sampling_func(r) for r in responses]

        # Normalize the fitness scores.
        fitness_scores /= np.sum(fitness_scores)
        fitness_scores = np.squeeze(fitness_scores)

        # Select parents probabilistically based on fitness scores.
        return np.random.choice(lineage.stimuli, size=batch_size, p=fitness_scores, replace=True)


class RegimeThreeMutationAssigner(MutationAssigner):
    def assign_mutation(self, lineage):
        return "RegimeThree"


class RegimeThreeMutationMagnitudeAssigner(MutationMagnitudeAssigner):

    def assign_mutation_magnitude(self, lineage: Lineage, stimulus: Stimulus) -> float:
        pass


class RegimeThreeTransitioner(RegimeTransitioner):
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
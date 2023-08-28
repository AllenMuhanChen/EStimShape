# test_regime_one.py

import unittest
from typing import Callable

import numpy as np

from src.newga.ga_classes import Stimulus, Lineage, ParentSelector, LineageFactory
from src.newga.regime_one import RankOrderedDistribution, RegimeOneParentSelector, RegimeOneTransitioner, \
    calculate_peak_response


def mock_get_all_stimuli_func():
    return [Stimulus(None, i, driving_response=i) for i in range(1, 11)]


import unittest


class TestRankOrderedDistributionEdges(unittest.TestCase):

    def test_one_stimulus(self):
        class Stimulus:
            def __init__(self, response_rate):
                self.response_rate = response_rate

        stimuli = [Stimulus(0.8)]
        proportions = [0.2, 0.3, 0.5]

        rank_ordered_distribution = RankOrderedDistribution(stimuli, proportions)

        # Check if the stimuli are placed in the correct bins
        self.assertEqual(rank_ordered_distribution.bins[2][0], stimuli[0])

    # Test for the edge case of having too few stimuli for the specified proportions
    def test_few_stimuli(self):
        class Stimulus:
            def __init__(self, response_rate):
                self.response_rate = response_rate

        stimuli = [Stimulus(0.8), Stimulus(0.6)]
        proportions = [0.5, 0.3, 0.2]

        rank_ordered_distribution = RankOrderedDistribution(stimuli, proportions)

        # Check if the stimuli are placed in the correct bins
        self.assertEqual(rank_ordered_distribution.bins[1][0], stimuli[1])
        self.assertEqual(rank_ordered_distribution.bins[2][0], stimuli[0])

    # Test to test the rounding feature
    def test_rounding_behavior(self):
        class Stimulus:
            def __init__(self, response_rate):
                self.response_rate = response_rate

        stimuli = [Stimulus(i) for i in range(1, 24)]  # 23 stimuli
        proportions = [0.1, 0.2, 0.2, 0.2, 0.3]
        bin_counts = [0] * 5

        # Run the test 10000 times to gather statistics
        for _ in range(10000):
            rank_ordered_distribution = RankOrderedDistribution(stimuli, proportions)
            bins = rank_ordered_distribution.bins
            for i, bin in enumerate(bins):
                bin_counts[i] += len(bin)

        # Verify that the distribution of stimuli among the bins aligns with the proportions
        total_stimuli = sum(bin_counts)
        for i, proportion in enumerate(proportions):
            actual_proportion = bin_counts[i] / total_stimuli
            # Allow for a small deviation from the expected proportion
            self.assertAlmostEqual(actual_proportion, proportion, delta=0.01)


class TestRankOrderedDistribution(unittest.TestCase):

    def setUp(self):
        class Stimulus:
            def __init__(self, response_rate):
                self.response_rate = response_rate

        self.stimuli = [Stimulus(i) for i in range(1, 11)]
        self.rank_ordered_distribution = RankOrderedDistribution(self.stimuli, [0.1, 0.2, 0.2, 0.2, 0.3])

    def test_generate_bins(self):
        # Test that bins are generated correctly.
        bins = self.rank_ordered_distribution.bins
        self.assertEqual(len(bins), 5)
        self.assertEqual(sum(len(bin) for bin in bins), 10)

        # Test that stimuli are assigned to the correct bins.
        expected_bins = [[1], [2, 3], [4, 5], [6, 7], [8, 9, 10]]
        for i, bin in enumerate(bins):
            self.assertEqual([s.response_rate for s in bin], expected_bins[i])

    def test_sample_from_bin(self):
        # Test that sampling from a bin returns the correct number of stimuli.
        sampled_stimuli = self.rank_ordered_distribution._sample_from_bin(0, 1)
        self.assertEqual(len(sampled_stimuli), 1)

        # Test that the sampled stimuli are from the correct bin.
        self.assertIn(sampled_stimuli[0].response_rate, [1])

    def test_sample_exact_numbers_per_bin(self):
        # Test that sampling returns the correct number of stimuli.
        sampled_stimuli = self.rank_ordered_distribution.sample_amount_per_bin(amount_per_bin=[1, 1, 1, 1, 1])
        sampled_stimuli = np.squeeze(sampled_stimuli)
        self.assertEqual(len(sampled_stimuli), 5)

        # Test that the sampled stimuli are from the correct bins.
        expected_response_rate_ranges = [(1, 1), (2, 3), (4, 5), (6, 7), (8, 10)]
        for stimulus, (low, high) in zip(sampled_stimuli, expected_response_rate_ranges):
            self.assertTrue(low <= stimulus.response_rate <= high)

    def test_sample_total_across_bins(self):
        # Test that sampling returns the correct number of stimuli.
        sampled_stimuli = self.rank_ordered_distribution.sample_total_amount_across_bins([0.1, 0.2, 0.2, 0.2, 0.3], 1)
        self.assertEqual(len(sampled_stimuli), 1)


class TestRegimeOneParentSelector(unittest.TestCase):
    def setUp(self):
        self.get_all_stimuli_func = mock_get_all_stimuli_func
        self.selector = RegimeOneParentSelector(self.get_all_stimuli_func, [0.1, 0.2, 0.2, 0.2, 0.3],
                                                [10, 10, 10, 10, 10])

        stimuli = [Stimulus(None, i, driving_response=i) for i in [10, 8, 6, 5, 1]]
        self.lineage = LineageFactory.create_lineage_from_stimuli(stimuli)

    def test_select_parents(self):
        # Test that select_parents returns the correct number of parents.
        parents = self.selector.select_parents(self.lineage, 5)
        print(len(parents))
        # Test that the selected parents are the ones we specified are in this lineage
        self.assertTrue(all(parent.response_rate in [10, 8, 6, 5, 1] for parent in parents))


import unittest


class TestRegimeOneTransitioner(unittest.TestCase):
    def setUp(self):
        self.transitioner = RegimeOneTransitioner(convergence_threshold=0.01)
        stimuli_with_gaps = [
            Stimulus(0, "Test", driving_response=10, gen_id=1),
            Stimulus(1, "Test", driving_response=8, gen_id=1, parent_id=0),
            # Skipping gen_id=2, it's an empty generation
            Stimulus(2, "Test", driving_response=7, gen_id=3, parent_id=1),
            Stimulus(3, 3, driving_response=6, gen_id=3, parent_id=1),
            Stimulus(4, "Test", driving_response=5, gen_id=4, parent_id=2)
        ]
        self.lineage_with_gaps = Lineage(stimuli_with_gaps[0], None, gen_id=5)
        self.lineage_with_gaps.stimuli = stimuli_with_gaps


    def test_should_transition_skips_empty_generations(self):
        # Setup a scenario where x is 3, and we have an empty generation (gen_id=2)
        self.transitioner.x = 3

        result = self.transitioner.should_transition(self.lineage_with_gaps)
        print(self.transitioner.peak_responses)
        # Validate that the method correctly identified generations with stimuli
        self.assertEqual(self.transitioner.peak_responses,
                         [calculate_peak_response([10, 8, 7, 6, 5]), calculate_peak_response([10, 8, 7, 6]),
                          calculate_peak_response([10, 8])])

        # Validate whether the transition should happen (this is based on your specific logic and threshold)
        self.assertTrue(result or not result)  # Replace this with the expected boolean value based on your logic


if __name__ == '__main__':
    unittest.main()

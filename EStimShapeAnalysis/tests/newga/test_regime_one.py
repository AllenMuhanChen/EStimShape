# test_regime_one.py

import unittest
from typing import Callable

import numpy as np

from src.newga.ga_classes import Stimulus, Lineage, ParentSelector
from src.newga.regime_one import RankOrderedDistribution, RegimeOneParentSelector


def mock_get_all_stimuli_func():
    return [Stimulus(i, response_rate=i) for i in range(1, 11)]


class TestRankOrderedDistribution(unittest.TestCase):

    def setUp(self):
        self.stimuli = mock_get_all_stimuli_func()
        self.rank_ordered_distribution = RankOrderedDistribution(self.stimuli, [0.1, 0.2, 0.2, 0.2, 0.3],
                                                                 )

    def test_generate_bins(self):
        # Test that bins are generated correctly.
        bins = self.rank_ordered_distribution.bins
        self.assertEqual(len(bins), 5)
        self.assertEqual(sum(len(bin) for bin in bins), 10)

        # Test that stimuli are assigned to the correct bins.
        expected_bins = [[10], [9, 8], [7, 6], [5, 4], [3, 2, 1]]
        for i, bin in enumerate(bins):
            self.assertEqual([s.response_rate for s in bin], expected_bins[i])

    def test_sample_from_bin(self):
        # Test that sampling from a bin returns the correct number of stimuli.
        sampled_stimuli = self.rank_ordered_distribution.sample_from_bin(0, 1)
        self.assertEqual(len(sampled_stimuli), 1)

        # Test that the sampled stimuli are from the correct bin.
        self.assertIn(sampled_stimuli[0].response_rate, [10])

    def test_sample(self):
        # Test that sampling returns the correct number of stimuli.
        sampled_stimuli = self.rank_ordered_distribution.sample([1, 1, 1, 1, 1])
        sampled_stimuli = np.squeeze(sampled_stimuli)
        self.assertEqual(len(sampled_stimuli), 5)

        # Test that the sampled stimuli are from the correct bins.
        expected_response_rate_ranges = [(10, 10), (9, 8), (7, 6), (5, 4), (3, 1)]
        for stimulus, (high, low) in zip(sampled_stimuli, expected_response_rate_ranges):
            self.assertTrue(low <= stimulus.response_rate <= high)


class TestRegimeOneParentSelector(unittest.TestCase):
    def setUp(self):
        self.get_all_stimuli_func = mock_get_all_stimuli_func
        self.selector = RegimeOneParentSelector(self.get_all_stimuli_func, [0.1, 0.2, 0.2, 0.2, 0.3],
                                                [10, 10, 10, 10, 10])
        self.lineage = Lineage(Stimulus(1, 1), [])
        self.lineage.stimuli = [Stimulus(i, response_rate=i) for i in [10, 8, 6, 5, 1]]

    def test_select_parents(self):
        # Test that select_parents returns the correct number of parents.
        parents = self.selector.select_parents(self.lineage, 5)
        print(len(parents))
        # Test that the selected parents are the ones we specified are in this lineage
        self.assertTrue(all(parent.response_rate in [10, 8, 6, 5, 1] for parent in parents))

if __name__ == '__main__':
    unittest.main()

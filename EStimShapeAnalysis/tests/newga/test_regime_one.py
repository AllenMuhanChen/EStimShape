# test_regime_one.py

import unittest
from src.newga.ga_classes import Stimulus
from regime_one import RankOrderedDistribution, RegimeOneParentSelector

class TestRankOrderedDistribution(unittest.TestCase):
    def setUp(self):
        self.stimuli = [Stimulus("Test", response_rate=i) for i in range(10)]
        self.rank_ordered_distribution = RankOrderedDistribution(self.stimuli, [0.1, 0.2, 0.2, 0.2, 0.3])

    def test_generate_bins(self):
        # Test that bins are generated correctly.
        bins = self.rank_ordered_distribution.bins
        self.assertEqual(len(bins), 5)
        self.assertEqual(sum(len(bin) for bin in bins), 10)

        # Test that stimuli are assigned to the correct bins.
        expected_bins = [[9], [8, 7], [6, 5], [4, 3], [2, 1, 0]]
        for i, bin in enumerate(bins):
            self.assertEqual([s.response_rate for s in bin], expected_bins[i])

    def test_sample_from_bin(self):
        # Test that sample_from_bin returns the correct number of stimuli.
        stimuli = self.rank_ordered_distribution.sample_from_bin(0, 3)
        self.assertEqual(len(stimuli), 3)

        # Test that sample_from_bin returns the correct stimuli.
        expected_stimuli = [9, 9, 9]
        self.assertEqual([s.response_rate for s in stimuli], expected_stimuli)



class TestRegimeOneParentSelector(unittest.TestCase):
    def setUp(self):
        self.selector = RegimeOneParentSelector()

    def test_select_parents(self):
        # Test that select_parents returns the correct number of parents.
        stimuli = [Stimulus(response_rate=i) for i in range(10)]
        parents = self.selector.select_parents(stimuli, 3)
        self.assertEqual(len(parents), 3)

        # Test that the selected parents are the ones with the highest response rates.
        self.assertTrue(all(parent in stimuli[-3:] for parent in parents))


if __name__ == '__main__':
    unittest.main()

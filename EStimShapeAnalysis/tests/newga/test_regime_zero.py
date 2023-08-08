# test_regime_zero.py

import unittest
from src.newga.ga_classes import Stimulus, Lineage, Node, LineageFactory
from src.newga.regime_zero import RegimeZeroTransitioner


class TestRegimeZeroTransitioner(unittest.TestCase):
    def setUp(self):
        self.transitioner = RegimeZeroTransitioner(spontaneous_firing_rate=10, significance_level=0.05)

    def test_should_transition(self):
        # Generate some stimuli with high response rates
        stimuli = [Stimulus(None, "Test", response_vector=[20 for _ in range(30)])]
        tree = Node(stimuli[0])
        for stimulus in stimuli[1:]:
            tree.add_child(stimulus)
        lineage = LineageFactory.create_lineage_from_tree(tree)

        # The t-test should find that the response rates are significantly higher than the spontaneous firing rate,
        # so should_transition should return True
        self.assertTrue(self.transitioner.should_transition(lineage))

        # Generate some stimuli with low response rates
        stimuli = [Stimulus(None, "Test", response_vector=[10 for _ in range(30)])]
        tree = Node(stimuli[0])
        for stimulus in stimuli[1:]:
            tree.add_child(stimulus)
        lineage = LineageFactory.create_lineage_from_tree(tree)

        # The t-test should find that the response rates are not significantly different from the spontaneous firing rate,
        # so should_transition should return False
        self.assertFalse(self.transitioner.should_transition(lineage))


if __name__ == '__main__':
    unittest.main()

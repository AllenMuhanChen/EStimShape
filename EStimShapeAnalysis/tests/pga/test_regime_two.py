import unittest

from pga.regime_type import RegimeType
from src.pga.ga_classes import Stimulus, Lineage, Node, LineageFactory
from src.pga.regime_two import CanopyPhaseParentSelector, CanopyPhaseTransitioner


class TestRegimeTwoParentSelector(unittest.TestCase):
    def setUp(self):
        self.selector = CanopyPhaseParentSelector(0.5, 2)

    def test_select_parents(self):
        lineage = LineageFactory.create_lineage_from_stimuli([Stimulus(None, "Test", response_rate=i) for i in range(1, 11)])
        parents = self.selector.select_parents(lineage, 3)

        # Test that select_parents returns the correct number of parents.
        self.assertEqual(len(parents), 3)

        # Test that the selected parents are the ones with the highest response rates.
        self.assertTrue(all(parent.response_rate in [10, 9] for parent in parents))

    def test_select_parents_threshold(self):
        # Test that select_parents returns only top 2 parents that have passed the threshold
        # Which is either id 9 or 10 because we only get the top x. In this case x is 2
        stimuli = [Stimulus(i, "Test", response_rate=i) for i in range(0, 11)]
        lineage = LineageFactory.create_lineage_from_stimuli(stimuli)
        parents = self.selector.select_parents(lineage, 3)
        print([parent.response_rate for parent in parents])
        self.assertTrue(all(parent.id in [9, 10] for parent in parents))


class TestRegimeTwoTransitioner(unittest.TestCase):
    def setUp(self):
        self.transitioner = CanopyPhaseTransitioner(2, 2)

    def test_should_transition(self):


        # Create a parent-child pair with a high response rate ratio.
        parent_stimulus = Stimulus(1, "Test", response_rate=10)
        child_stimulus_1 = Stimulus(2, RegimeType.REGIME_TWO.value, response_rate=10, parent_id=1)


        # Create a parent-child pair with a low response rate ratio.
        child_stimulus_2 = Stimulus(3, RegimeType.REGIME_TWO.value, response_rate=2, parent_id=1)
        tree = Node(parent_stimulus)
        tree.add_child(child_stimulus_1)
        tree.add_child(child_stimulus_2)
        lineage = LineageFactory.create_lineage_from_tree(tree)

        # The threshold is 2 high 2 low so we should not transition
        # because we only have 1 high 1 low.
        self.assertFalse(self.transitioner.should_transition(lineage))


        # The threshold is 2 high 2 low, so add two more stimuli to the lineage and we should transition now
        child_stimulus_3 = Stimulus(4, RegimeType.REGIME_TWO.value, response_rate=10, parent_id=1)
        child_stimulus_4 = Stimulus(5, RegimeType.REGIME_TWO.value, response_rate=2, parent_id=1)
        tree.add_child(child_stimulus_3)
        tree.add_child(child_stimulus_4)
        lineage = LineageFactory.create_lineage_from_tree(tree)

        self.assertTrue(self.transitioner.should_transition(lineage))

if __name__ == '__main__':
    unittest.main()

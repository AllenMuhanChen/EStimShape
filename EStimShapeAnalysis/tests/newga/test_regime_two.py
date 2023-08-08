import unittest
from src.newga.ga_classes import Stimulus, Lineage, Node
from src.newga.regime_two import RegimeTwoParentSelector, RegimeTwoTransitioner


class TestRegimeTwoParentSelector(unittest.TestCase):
    def setUp(self):
        self.selector = RegimeTwoParentSelector(0.5, 2)

    def test_select_parents(self):
        lineage = Lineage(Stimulus(None, "Test"), [])
        lineage.stimuli = [Stimulus(None, "Test", driving_response=i) for i in range(1, 11)]
        parents = self.selector.select_parents(lineage, 3)

        # Test that select_parents returns the correct number of parents.
        self.assertEqual(len(parents), 3)

        # Test that the selected parents are the ones with the highest response rates.
        self.assertTrue(all(parent.response_rate in [10, 9] for parent in parents))

    def test_select_parents_threshold(self):
        # Test that select_parents returns only parents that have passed the threshold
        lineage = Lineage(Stimulus(None, "Test"), [])
        lineage.stimuli = [Stimulus(None, "Test", driving_response=i) for i in range(1, 11)]
        lineage.stimuli[0].parent = Stimulus(None, "Test", driving_response=9)
        lineage.stimuli[0].response_rate = 10
        lineage.stimuli[1].parent = Stimulus(None, "Test", driving_response=10)
        lineage.stimuli[1].response_rate = 2
        parents = self.selector.select_parents(lineage, 3)
        self.assertTrue(all(parent.response_rate in [10] for parent in parents))


class TestRegimeTwoTransitioner(unittest.TestCase):
    def setUp(self):
        self.transitioner = RegimeTwoTransitioner(2, 2)

    def test_should_transition(self):


        # Create a parent-child pair with a high response rate ratio.
        parent_stimulus = Stimulus(1, "Test", driving_response=10)
        child_stimulus_1 = Stimulus(2, "Test", driving_response=10, parent_id=1)


        # Create a parent-child pair with a low response rate ratio.
        child_stimulus_2 = Stimulus(3, "Test", driving_response=2, parent_id=1)
        tree = Node(parent_stimulus)
        tree.add_child(child_stimulus_1)
        tree.add_child(child_stimulus_2)
        lineage = Lineage(parent_stimulus, [], tree=tree)

        # The threshold is 2 high 2 low so we should not transition
        # because we only have 1 high 1 low.
        self.assertFalse(self.transitioner.should_transition(lineage))


        # The threshold is 2 high 2 low, so add two more stimuli to the lineage and we should transition now
        child_stimulus_3 = Stimulus(4, "Test", driving_response=10, parent_id=1)
        child_stimulus_4 = Stimulus(5, "Test", driving_response=2, parent_id=1)
        tree.add_child(child_stimulus_3)
        tree.add_child(child_stimulus_4)
        lineage = Lineage(parent_stimulus, [], tree=tree)

        self.assertTrue(self.transitioner.should_transition(lineage))

if __name__ == '__main__':
    unittest.main()

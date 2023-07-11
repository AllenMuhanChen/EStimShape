import unittest
from src.newga.ga_classes import Stimulus, Lineage
from src.newga.regime_two import RegimeTwoParentSelector, RegimeTwoTransitioner


class TestRegimeTwoParentSelector(unittest.TestCase):
    def setUp(self):
        self.selector = RegimeTwoParentSelector(0.5, 2)

    def test_select_parents(self):
        lineage = Lineage(Stimulus("Test", 1), [])
        lineage.stimuli = [Stimulus("Test", response_rate=i) for i in range(1, 11)]
        parents = self.selector.select_parents(lineage, 3)

        # Test that select_parents returns the correct number of parents.
        self.assertEqual(len(parents), 3)

        # Test that the selected parents are the ones with the highest response rates.
        self.assertTrue(all(parent.response_rate in [10, 9] for parent in parents))

    def test_select_parents_threshold(self):
        # Test that select_parents returns only parents that have passed the threshold
        lineage = Lineage(Stimulus("Test", 1), [])
        lineage.stimuli = [Stimulus("Test", response_rate=i) for i in range(1, 11)]
        lineage.stimuli[0].parent = Stimulus("Test", response_rate=9)
        lineage.stimuli[0].response_rate = 10
        lineage.stimuli[1].parent = Stimulus("Test", response_rate=10)
        lineage.stimuli[1].response_rate = 2
        parents = self.selector.select_parents(lineage, 3)
        self.assertTrue(all(parent.response_rate in [10] for parent in parents))


class TestRegimeTwoTransitioner(unittest.TestCase):
    def setUp(self):
        self.transitioner = RegimeTwoTransitioner(2, 2)

    def test_should_transition(self):
        lineage = Lineage(Stimulus(1, 1), [])
        lineage.stimuli = [Stimulus("Test") for i in range(1, 5)]

        # Create a parent-child pair with a high response rate ratio.
        lineage.stimuli[0].parent = Stimulus(1, response_rate=10)
        lineage.stimuli[0].response_rate = 10

        # Create a parent-child pair with a low response rate ratio.
        lineage.stimuli[1].parent = Stimulus(2, response_rate=10)
        lineage.stimuli[1].response_rate = 2

        self.assertFalse(self.transitioner.should_transition(lineage))

        # Create a parent-child pair with a high response rate ratio.
        lineage.stimuli[2].parent = Stimulus(3, response_rate=10)
        lineage.stimuli[2].response_rate = 10

        self.assertFalse(self.transitioner.should_transition(lineage))

        # Create a parent-child pair with a low response rate ratio.
        lineage.stimuli[3].parent = Stimulus(4, response_rate=10)
        lineage.stimuli[3].response_rate = 2

        self.assertTrue(self.transitioner.should_transition(lineage))

if __name__ == '__main__':
    unittest.main()

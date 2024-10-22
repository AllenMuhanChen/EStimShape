import unittest

from src.pga.alexnet.alexnet_config import RFLocPhaseParentSelector, RFLocPhaseMutationMagnitudeAssigner
from src.pga.ga_classes import Stimulus, LineageFactory


class TestAlexNetPhases(unittest.TestCase):
    def setUp(self) -> None:
        self.stimuli = [Stimulus(i, i, response_rate=i) for i in [10, 8, 6, 5, 1]]
        self.lineage = LineageFactory.create_lineage_from_stimuli(self.stimuli)

    def test_select_parent(self):
        parentSelector = RFLocPhaseParentSelector()
        selected_parents = parentSelector.select_parents(self.lineage, 3)

        self.assertEqual(len(selected_parents), 3)
        self.assertEqual(selected_parents[0].response_rate, 10)
        self.assertEqual(selected_parents[1].response_rate, 8)
        self.assertEqual(selected_parents[2].response_rate, 6)


    def test_mutation_magnitude(self):
        mutationAssigner = RFLocPhaseMutationMagnitudeAssigner()
        mutation_magnitude = mutationAssigner.assign_mutation_magnitude(self.lineage, self.stimuli[0])
        print(mutation_magnitude)
        mutation_magnitude = mutationAssigner.assign_mutation_magnitude(self.lineage, self.stimuli[1])
        print(mutation_magnitude)
        mutation_magnitude = mutationAssigner.assign_mutation_magnitude(self.lineage, self.stimuli[2])
        print(mutation_magnitude)




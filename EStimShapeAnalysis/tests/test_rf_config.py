import random
import unittest
from typing import List

from src.pga.zooming_phase import ZoomSetHandler, ZoomingPhaseParentSelector, ZoomingPhaseMutationAssigner
from src.pga.ga_classes import Stimulus, LineageFactory


class TestZoomingPhase(unittest.TestCase):

    def setUp(self):
        zoom_set_handler = MockZoomSetHandler()
        self.selector = ZoomingPhaseParentSelector(
            spontaneous_firing_rate=15,
            significance_level=0.05,
            zoom_set_handler=zoom_set_handler
        )
        self.assigner = ZoomingPhaseMutationAssigner(
            zoom_set_handler=zoom_set_handler
        )

        stimuli = [Stimulus(i, "Test", response_rate=i, response_vector=[i for _ in range(10)]) for i in
                   [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]]
        # shuffle stimuli randomly
        random.shuffle(stimuli)

        self.lineage = LineageFactory.create_lineage_from_stimuli(stimuli)

    def test_select_parents(self):
        actual_parents = self.selector.select_parents(self.lineage, 10)
        actual_parents_responses = [parent.response_rate for parent in actual_parents]
        expected_parents_responses = [50, 40, 30, 30, 20, 20]

        self.assertEqual(actual_parents_responses, expected_parents_responses)

    def test_assign_mutation(self):
        actual_assigned_mutations: List[str] = []

        actual_parents = self.selector.select_parents(self.lineage, 10)

        for stim in actual_parents:
            actual_assigned_mutations.append(self.assigner.assign_mutation(self.lineage, stim))

        print(actual_assigned_mutations)
        expected_assigned_mutations = ['Zooming_2', 'Zooming_2', 'Zooming_1', 'Zooming_2', 'Zooming_1', 'Zooming_2']

        self.assertEqual(actual_assigned_mutations, expected_assigned_mutations)


class MockZoomSetHandler(ZoomSetHandler):
    all_comps = [1, 2]
    comp_map = {
        20: [],
        30: [],
        40: [1],
        50: [1],
    }

    def is_empty_set(self, stimulus: Stimulus) -> bool:
        if stimulus.response_rate == 20 or stimulus.response_rate == 30:
            return True

    def is_partial_set(self, stimulus):
        if stimulus.response_rate == 40 or stimulus.response_rate == 50:
            return True

    def is_full_set(self, stimulus):
        if stimulus.response_rate > 50:
            return True

    def get_how_many_stimuli_needed_to_make_full_set(self, stimulus):
        if self.is_partial_set(stimulus):
            return 1
        elif self.is_empty_set(stimulus):
            return 2

    def get_next_comp_to_zoom(self, parent):
        current_zoomed: List[int] = self.comp_map[parent.id]
        for comp in self.all_comps:
            if comp not in current_zoomed:
                self.comp_map[parent.id].append(comp)  # update
                return comp


from clat.util.connection import Connection


def test__get_num_comps_in():
    conn = Connection("allen_estimshape_ga_test_240508")
    handler = ZoomSetHandler(conn=conn)
    num_comps = handler._get_num_comps_in(Stimulus(1715196706133280, "Test"))
    print(num_comps)
    assert num_comps == 2


def test_get_next():
    conn = Connection("allen_estimshape_ga_test_240508")
    handler = ZoomSetHandler(conn=conn)
    next_comp = handler.get_next_comp_to_zoom(Stimulus(1715196706133280, "Test"))
    print(next_comp)

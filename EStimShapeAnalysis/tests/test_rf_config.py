import random
import unittest
from typing import List

from src.pga.zooming_phase import ZoomSetHandler, ZoomingPhaseParentSelector, ZoomingPhaseMutationAssigner, \
    ZoomingSideTest
from src.pga.ga_classes import Stimulus, Lineage, LineageFactory


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


class TestZoomingSideTest(unittest.TestCase):
    GEN_ID = 5
    PREV_GEN = GEN_ID - 1

    def setUp(self):
        self.zoom_set_handler = SideTestMockZoomSetHandler()
        self.side_test = ZoomingSideTest(
            zoom_set_handler=self.zoom_set_handler,
            n_top_responders=2,
            after_regime_index=1,
        )

    def _single_stim_lineage(self, stim: Stimulus, current_regime_index: int) -> Lineage:
        lineage = LineageFactory.create_lineage_from_stimuli([stim])
        lineage.current_regime_index = current_regime_index
        return lineage

    def _zoom_children(self, lineage: Lineage):
        founder = lineage.tree.data
        return [s for s in lineage.stimuli if s is not founder and "Zooming" in s.mutation_type]

    def test_makes_full_zoom_sets_for_global_top_n(self):
        # Three eligible lineages past the zooming phase; top 2 responders should be zoomed.
        high = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=50, gen_id=self.PREV_GEN), 2)
        mid = self._single_stim_lineage(
            Stimulus(2, "REGIME_ONE", response_rate=30, gen_id=self.PREV_GEN), 2)
        low = self._single_stim_lineage(
            Stimulus(3, "REGIME_ONE", response_rate=10, gen_id=self.PREV_GEN), 2)

        self.side_test.run([high, mid, low], self.GEN_ID)

        # Top 2 (resp 50 and 30) each get a full zoom set of 2 components.
        self.assertEqual([c.mutation_type for c in self._zoom_children(high)], ["Zooming_1", "Zooming_2"])
        self.assertEqual([c.mutation_type for c in self._zoom_children(mid)], ["Zooming_1", "Zooming_2"])
        # The lowest responder is not in the top N, so it is untouched.
        self.assertEqual(self._zoom_children(low), [])
        # New zoom stimuli are tagged with the current generation and parented correctly.
        for child in self._zoom_children(high):
            self.assertEqual(child.gen_id, self.GEN_ID)
            self.assertEqual(child.parent_id, 1)

    def test_skips_lineages_not_past_zooming_phase(self):
        # Highest responder overall, but its lineage is still in the zooming phase (index 1).
        in_zooming = self._single_stim_lineage(
            Stimulus(1, "REGIME_ONE", response_rate=100, gen_id=self.PREV_GEN), 1)
        past_zooming = self._single_stim_lineage(
            Stimulus(2, "REGIME_ONE", response_rate=30, gen_id=self.PREV_GEN), 2)

        self.side_test.run([in_zooming, past_zooming], self.GEN_ID)

        self.assertEqual(self._zoom_children(in_zooming), [])
        self.assertEqual([c.mutation_type for c in self._zoom_children(past_zooming)], ["Zooming_1", "Zooming_2"])

    def test_filters_ineligible_stimuli(self):
        # Use a generous N so this test exercises eligibility, not top-N truncation.
        side_test = ZoomingSideTest(
            zoom_set_handler=SideTestMockZoomSetHandler(),
            n_top_responders=10,
            after_regime_index=1,
        )

        # These should never be zoomed regardless of how high they respond.
        already_zoomed = self._single_stim_lineage(
            Stimulus(1, "Zooming_1", response_rate=90, gen_id=self.PREV_GEN), 2)
        catch = self._single_stim_lineage(
            Stimulus(2, "CATCH", response_rate=90, gen_id=self.PREV_GEN), 2)
        baseline = self._single_stim_lineage(
            Stimulus(3, "BASELINE", response_rate=90, gen_id=self.PREV_GEN), 2)
        no_response = self._single_stim_lineage(
            Stimulus(5, "REGIME_ONE", response_rate=None, gen_id=self.PREV_GEN), 2)
        wrong_gen = self._single_stim_lineage(
            Stimulus(6, "REGIME_ONE", response_rate=90, gen_id=self.PREV_GEN - 1), 2)

        # SIDETEST stimuli (e.g. 2D-vs-3D) are valid zoom targets, just like regular stimuli.
        side_test_stim = self._single_stim_lineage(
            Stimulus(4, "SIDETEST_2Dvs3D", response_rate=90, gen_id=self.PREV_GEN), 2)
        eligible = self._single_stim_lineage(
            Stimulus(7, "REGIME_ONE", response_rate=20, gen_id=self.PREV_GEN), 2)

        lineages = [already_zoomed, catch, baseline, side_test_stim, no_response, wrong_gen, eligible]
        side_test.run(lineages, self.GEN_ID)

        for lineage in [already_zoomed, catch, baseline, no_response, wrong_gen]:
            self.assertEqual(self._zoom_children(lineage), [])
        # SIDETEST and regular stimuli both get full zoom sets.
        self.assertEqual([c.mutation_type for c in self._zoom_children(side_test_stim)], ["Zooming_1", "Zooming_2"])
        self.assertEqual([c.mutation_type for c in self._zoom_children(eligible)], ["Zooming_1", "Zooming_2"])


class SideTestMockZoomSetHandler(ZoomSetHandler):
    all_comps = [1, 2]

    def __init__(self):
        self.comp_map = {}

    def get_how_many_stimuli_needed_to_make_full_set(self, stimulus: Stimulus) -> int:
        zoomed = self.comp_map.get(stimulus.id, [])
        return len(self.all_comps) - len(zoomed)

    def get_next_comp_to_zoom(self, parent: Stimulus) -> int:
        zoomed = self.comp_map.setdefault(parent.id, [])
        for comp in self.all_comps:
            if comp not in zoomed:
                zoomed.append(comp)
                return comp
        raise ValueError("No remaining components to choose from.")


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

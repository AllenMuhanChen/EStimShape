from __future__ import annotations
import unittest
from unittest.mock import Mock

from intan.channels import Channel
from intan.response_processing import ResponseProcessor
from newga.ga_classes import Node
from newga.genetic_algorithm import GeneticAlgorithm
from newga.multi_ga_db_util import LineageGaInfoEntry, StimGaInfoEntry


class TestConstructLineages(unittest.TestCase):
    def setUp(self) -> None:
        self.setup_db_util_mock()
        self.setup_response_processor_mock(self.db_util_mock)

        self.ga_mock = GeneticAlgorithm(name="Test_GA",
                                        db_util=self.db_util_mock,
                                        regimes=None,
                                        trials_per_generation=40,
                                        lineage_distributor=None,
                                        response_parser=None,
                                        response_processor=self.response_processor_mock)

    def setup_db_util_mock(self):
        self.db_util_mock = Mock()
        self.db_util_mock.read_lineage_ga_info_for_experiment_id_and_gen_id.return_value = [LineageGaInfoEntry(
            lineage_id=0,
            tree_spec=self._mock_tree_spec(),
            regime="REGIME_ZERO",
            lineage_data="Test Regime Data",
            gen_id=0,
            experiment_id=0,
        )]

        def mock_stim_ga_info_entry(stim_id: int) -> StimGaInfoEntry:
            return StimGaInfoEntry(stim_id=stim_id, parent_id=-1, lineage_id=0, stim_type="REGIME_ZERO",
                                   response=self.db_util_mock.read_responses_for(stim_id), gen_id=0)

        self.db_util_mock.read_stim_ga_info_entry = mock_stim_ga_info_entry

        self.db_util_mock.read_current_cluster.return_value = [Channel.A_000]

        self.db_util_mock.read_responses_for = lambda stim_id, channel=None: float(stim_id) * 10

    def setup_response_processor_mock(self, db_util):
        self.response_processor_mock = ResponseProcessor(db_util, sum)

    def _mock_tree_spec(self):
        mock_tree = Node(1)
        mock_tree.add_child(Node(2))
        mock_tree.add_child(Node(3))
        mock_tree.add_child_to(3, Node(4))
        return mock_tree.to_xml()

    def test_construct_lineages_from_db(self):
        self.ga_mock._construct_lineages_from_db()
        print(self.ga_mock.lineages[0].stimuli[0].response_rate)
        print(self.ga_mock.lineages[0].stimuli[1].response_rate)
        print(self.ga_mock.lineages[0].stimuli[2].response_rate)
        print(self.ga_mock.lineages[0].stimuli[3].response_rate)

import unittest
from unittest.mock import Mock

from newga.lineage_selection import RegimeType, DatabaseLineageDistributor, filter_by_regime_past, \
    distribute_amount_equally_among
from newga.multi_ga_db_util import MultiGaDbUtil


def mock_read_regime_for_lineage(lineage_id: int) -> str:
    if lineage_id == 0:
        return "REGIME_ZERO"
    elif lineage_id == 1:
        return "REGIME_ONE"
    elif lineage_id == 2:
        return "REGIME_TWO"
    elif lineage_id == 3:
        return "REGIME_THREE"


class TestClassicLineageDistributor(unittest.TestCase):
    pass

class TestRegimeEnum(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.mock_db_util = Mock()
        self.mock_db_util.read_regime_for_lineage = mock_read_regime_for_lineage
        self.mock_db_util.read_lineage_ids_for_experiment_id.return_value = [0, 1, 2, 3]

        self.mock_db_util.read_stim_ids_for_lineage = lambda lineage_id: [item * lineage_id for item in
                                                                          [1, 1, 1, 5, 5, 5]]
        self.mock_db_util.read_driving_response = lambda stim_id: stim_id

        self.distributor = DatabaseLineageDistributor(self.mock_db_util, 40, [], 2)

    def test_distribute_trials(self):
        # Qualifying Lineages:
        # Lineage 2
        # Lineage 3
        # If above threshold for num to build then distribute equally between those that qualify:
        num_trials_for_lineages = self.distributor.get_num_trials_for_lineage_ids("Test")
        self.assertEqual(num_trials_for_lineages, {2: 20, 3: 20})

        # If below threshold for num to build then distribute equally between all:
        self.distributor.number_of_lineages_to_build = 3
        num_trials_for_lineages = self.distributor.get_num_trials_for_lineage_ids("Test")
        self.assertEqual(num_trials_for_lineages, {0: 10, 1: 10, 2: 10, 3: 10})

    def test_to_index(self):
        self.assertEqual(RegimeType.REGIME_ZERO.to_index(), 0)
        self.assertEqual(RegimeType.REGIME_ONE.to_index(), 1)
        self.assertEqual(RegimeType.REGIME_TWO.to_index(), 2)
        self.assertEqual(RegimeType.REGIME_THREE.to_index(), 3)

    def test_from_string(self):
        self.assertEqual(RegimeType("REGIME_ZERO"), RegimeType.REGIME_ZERO)
        self.assertEqual(RegimeType("REGIME_ONE"), RegimeType.REGIME_ONE)
        self.assertEqual(RegimeType("REGIME_TWO"), RegimeType.REGIME_TWO)
        self.assertEqual(RegimeType("REGIME_THREE"), RegimeType.REGIME_THREE)

    def test_read_regime_for_lineage(self):
        self.assertEqual(self.distributor._read_regime_for_lineage(0), RegimeType.REGIME_ZERO)

    def test_filter_by_regime(self):
        lineage_ids = self.mock_db_util.read_lineage_ids_for_experiment_id(None)
        regime_for_lineages = {lineage_id: self.distributor._read_regime_for_lineage(lineage_id) for lineage_id in
                               lineage_ids}
        lineages_with_regimes_past_one = filter_by_regime_past(1, regime_for_lineages)

        # Lineage Regimes:
        # Lineage 0: REGIME_ZERO
        # Lineage 1: REGIME_ONE
        # Lineage 2: REGIME_TWO
        # Lineage 3: REGIME_THREE
        # Threshold is 1, so only 2 and 3 should pass
        self.assertEqual(lineages_with_regimes_past_one, [2, 3])
        return lineages_with_regimes_past_one

    def test_filter_by_peak_response(self):

        lineages = self.test_filter_by_regime()

        # Peak Response for Each Lineage:
        # Lineage 0: 0
        # Lineage 1: 5
        # Lineage 2: 10
        # Lineage 3: 15

        # Threshold is 7.5, so only 2 and 3 should pass

        lineages_with_high_peak = self.distributor._filter_by_high_peak_response(lineages)
        self.assertEqual(lineages_with_high_peak, [2, 3])

    def test_distribute_equally_between(self):
        num_per_distributee = distribute_amount_equally_among(["A", "B", "C"], amount=4)
        # assert total sum of values is 4
        sum = 0
        for distributee, num in num_per_distributee.items():
            sum += num
        self.assertEqual(sum, 4)

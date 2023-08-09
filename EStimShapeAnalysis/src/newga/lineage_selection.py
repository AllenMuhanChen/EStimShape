from dataclasses import dataclass
from random import random
from typing import Any

from newga.ga_classes import LineageDistributor, Lineage, Regime, LineageFactory
from newga.multi_ga_db_util import MultiGaDbUtil

from newga.regime_one import calculate_peak_response
from newga.regime_type import RegimeType


def filter_by_regime_past(regime_index, regime_for_lineages: dict[int, RegimeType]) -> list[int]:
    return [lineage_id for lineage_id, regime in regime_for_lineages.items() if regime.to_index() > regime_index]


def filter_to_lineages_past_regime(regime_index: int, *, lineages: list[Lineage]) -> list[Lineage]:
    return [lineage for lineage in lineages if lineage.current_regime_index > regime_index]


def distribute_amount_equally_among(distributees: list[Any], *, amount: int) -> dict[Any: int]:
    lowest_whole_amount = amount // len(distributees)
    remainder = amount % len(distributees)
    amount_for_distributees = {distributee: lowest_whole_amount for distributee in distributees}
    if remainder > 0:
        for i in range(remainder):
            random_distributee = distributees[int(random() * len(distributees))]
            amount_for_distributees[random_distributee] += 1
    return amount_for_distributees


def filter_by_high_peak_response(lineages_with_regimes_past_regime_one, threshold=0.5):
    if len(lineages_with_regimes_past_regime_one) == 0:
        return []
    peak_response_for_lineages = get_peak_response_for(lineages_with_regimes_past_regime_one)
    max_peak_response = max(peak_response_for_lineages.values())
    lineages_with_high_enough_peak_responses = [lineage_id for lineage_id, peak_response in
                                                peak_response_for_lineages.items() if
                                                peak_response >= threshold * max_peak_response]
    return lineages_with_high_enough_peak_responses


def get_peak_response_for(lineages: list[Lineage]) -> dict[Lineage, float]:
    peak_response_for_lineages = {}
    for lineage in lineages:
        all_responses_in_lineage = [stimulus.response_rate for stimulus in lineage.stimuli]
        peak = calculate_peak_response(all_responses_in_lineage)
        peak_response_for_lineages[lineage] = peak
    return peak_response_for_lineages


@dataclass(kw_only=True)
class ClassicLineageDistributor():
    number_of_trials_per_generation: int
    max_lineages_to_build: int
    number_of_new_lineages_per_generation: int
    regimes: list[Regime]

    def get_num_trials_for_lineages(self, lineages: list[Lineage]) -> dict[Lineage: int]:
        lineages_with_regimes_past_regime_one = filter_to_lineages_past_regime(1, lineages=lineages)
        qualifying_lineages = filter_by_high_peak_response(lineages_with_regimes_past_regime_one)

        # If below threshold: distribute to all lineages equally and generate some new lineages
        num_lineages_to_distribute_between = len(qualifying_lineages)
        if num_lineages_to_distribute_between < self.max_lineages_to_build:
            num_trials_to_distribute_to_existing_lineages = self.number_of_trials_per_generation - self.number_of_new_lineages_per_generation
            num_trials_for_lineages = self.distribute_to_non_regime_zero_lineages(lineages, num_trials_to_distribute_to_existing_lineages)
            num_trials_for_lineages = self.add_new_lineages(num_trials_for_lineages, self.number_of_new_lineages_per_generation)

        # IF above threshold: distribute to qualifying lineages equally and don't generate new lineages
        else:
            num_trials_to_distribute_to_existing_lineages = self.number_of_trials_per_generation
            # Divide equally among qualifying lineages
            num_trials_for_lineages = distribute_amount_equally_among(qualifying_lineages,
                                                                      amount=num_trials_to_distribute_to_existing_lineages)

        return num_trials_for_lineages

    def add_new_lineages(self, num_trials_for_lineages: dict[Lineage: int], number_of_new_lineages):
        for new_lineage_index in range(number_of_new_lineages):
            new_lineage = LineageFactory.create_new_lineage(regimes=self.regimes)
            num_trials_for_lineages[new_lineage] = 1
        return num_trials_for_lineages

    def distribute_to_non_regime_zero_lineages(self, lineages, number_of_trials_to_distribute):
        non_regime_zero_lineages = filter_to_lineages_past_regime(0, lineages=lineages)
        num_trials_for_lineages = distribute_amount_equally_among(non_regime_zero_lineages, amount=number_of_trials_to_distribute)
        return num_trials_for_lineages


@dataclass
class DatabaseLineageDistributor(LineageDistributor):
    # Dependencies
    db_util: MultiGaDbUtil
    num_trials_per_generation: int
    regimes: list[Regime]
    number_of_lineages_to_build: int

    def get_num_trials_for_lineage_ids(self, experiment_id: int) -> dict[int: int]:
        # Read lineages from database and what regime they are on
        lineage_ids = self.db_util.read_lineage_ids_for_experiment_id(experiment_id)

        regime_for_all_lineages = {lineage_id: self._read_regime_for_lineage(lineage_id) for lineage_id in lineage_ids}

        lineages_with_regimes_past_regime_one = filter_by_regime_past(1, regime_for_all_lineages)
        qualifying_lineages = self._filter_by_high_peak_response(lineages_with_regimes_past_regime_one)

        # If below threshold: distribute to all lineages equally
        num_to_distribute_between = len(qualifying_lineages)
        if num_to_distribute_between < self.number_of_lineages_to_build:
            all_lineages = list(regime_for_all_lineages.keys())
            num_trials_for_lineages = distribute_amount_equally_among(all_lineages, amount=self.num_trials_per_generation)
        else:
            # Divide equally among qualifying lineages
            num_trials_for_lineages = distribute_amount_equally_among(qualifying_lineages, amount=self.num_trials_per_generation)

        return num_trials_for_lineages

    def _read_regime_for_lineage(self, lineage_id: int) -> RegimeType:
        regime_str = self.db_util.read_regime_for_lineage(lineage_id)
        return RegimeType(regime_str)

    def _filter_by_high_peak_response(self, lineages_with_regimes_past_regime_one, threshold=0.5):
        peak_response_for_lineages = self._get_peak_response_for_lineages(lineages_with_regimes_past_regime_one)
        max_peak_response = max(peak_response_for_lineages.values())
        lineages_with_high_enough_peak_responses = [lineage_id for lineage_id, peak_response in
                                                    peak_response_for_lineages.items() if
                                                    peak_response >= threshold * max_peak_response]
        return lineages_with_high_enough_peak_responses

    def _get_peak_response_for_lineages(self, lineages_with_regimes_past_regime_one):
        peak_response_for_lineages = {}
        for lineage_id in lineages_with_regimes_past_regime_one:
            stim_ids_in_lineage = self.db_util.read_stim_ids_for_lineage(lineage_id)
            driving_responses_of_lineage = [self.db_util.read_driving_response(stim_id) for stim_id in
                                            stim_ids_in_lineage]
            peak_response = calculate_peak_response(driving_responses_of_lineage)
            peak_response_for_lineages[lineage_id] = peak_response
        return peak_response_for_lineages



    # def read_lineages(self, lineage_ids: list[int]) -> list[Lineage]:
    #     lineages = []
    #     for lineage_id in lineage_ids:
    #         self.db_util.conn.execute(
    #             "SELECT tree_spec, lineage_data, gen_id, regime FROM LineageGaInfo WHERE lineage_id = %s",
    #             (lineage_id,)
    #         )
    #         tree_spec, lineage_data, gen_id, regime_str = self.db_util.conn.fetch_one()
    #
    #         # Extract stimuli for this lineage
    #         self.db_util.conn.execute(
    #             "SELECT stim_id, parent_id, ga_name, stim_type, response FROM StimGaInfo WHERE lineage_id = %s",
    #             (lineage_id,)
    #         )
    #         stimuli_data = self.db_util.conn.fetch_all()
    #
    #         stimuli = [Stimulus(*stim_data) for stim_data in stimuli_data]
    #
    #         founder = stimuli[0]  # Assuming the founder is the first stimulus in the list
    #         tree = Node.from_xml(tree_spec)
    #         regime = RegimeEnum(regime_str)  # We need to define this function to convert regime_str to Regime
    #
    #         lineage = Lineage(founder, self.regimes)
    #         lineage.stimuli = stimuli
    #         lineage.tree = tree
    #         lineage.gen_id = gen_id
    #         lineage.current_regime_index = int(regime.value[-1])
    #         lineages.append(lineage)

    #
    #     return lineages

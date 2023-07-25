from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from mysql.connector import DatabaseError

from intan.response_parsing import ResponseParser
from intan.response_processing import ResponseProcessor
from newga.multi_ga_db_util import MultiGaDbUtil
from src.newga.ga_classes import Regime, Lineage
from util import time_util


class LineageDistributor:

    def distribute(self, name) -> {Lineage: int}:
        pass


@dataclass
class GeneticAlgorithm:
    name: str
    regimes: List[Regime]
    db_util: MultiGaDbUtil
    trials_per_generation: int
    lineage_distributor: LineageDistributor
    response_parser: ResponseParser
    response_processor: ResponseProcessor

    experiment_id: int = field(init=False, default=None)
    gen_id: int = field(init=False, default=0)
    lineages: List[Lineage] = field(init=False, default_factory=list)

    def run(self):
        self.gen_id = self._read_gen_id()
        self.gen_id += 1

        if self.gen_id == 1:
            self._update_db_with_new_experiment()
            self._run_first_generation()
        elif self.gen_id > 1:
            self.response_parser.parse_to_db(self.name)
            self.response_processor.process_to_db(self.name)

            self._update_lineages_with_new_responses()
            self._run_next_generation()
        else:
            raise ValueError("gen_id must be >= 1")

        self._update_db()

    def _update_db_with_new_experiment(self):
        self.experiment_id = time_util.now()
        self.db_util.update_experiment_id(self.name, self.experiment_id)

    def _read_gen_id(self):
        try:
            gen_id_for_ga = self.db_util.read_ready_gas_and_generations_info()
            return gen_id_for_ga[self.name]
        except:
            raise DatabaseError("Cannot read gen_id for ga from InternalState table. ")

    def _run_first_generation(self):
        # Initialize lineages
        for trial in range(self.trials_per_generation):
            # generate id
            founder_id = time_util.now()
            self.lineages.append(Lineage(founder_id, self.regimes))

        # Run lineages
        for lineage in self.lineages:
            lineage.generate_new_batch()
            lineage.regime_transition()

    def _run_next_generation(self):
        num_trials_for_lineages = self.lineage_distributor.distribute(self.name)
        for lineage, num_trials in num_trials_for_lineages.items():
            lineage.generate_new_batch(num_trials)
            lineage.regime_transition()

    def _update_db(self) -> None:
        # Write lineages
        for lineage in self.lineages:
            lineage_data = ""
            self.db_util.write_lineage_ga_info(lineage.id, lineage.tree.to_xml(), lineage_data, self.gen_id,
                                               lineage.current_regime_index)

        # Write stimuli
        for lineage in self.lineages:
            for stim in lineage.stimuli:
                self.db_util.write_stim_ga_info(stim.id, stim.parent.id, self.name, lineage.gen_id, lineage.id,
                                                stim.mutation_type)

        # Update generations
        self.db_util.update_ready_gas_and_generations_info(self.name, self.gen_id)

    def _update_lineages_with_new_responses(self):
        for lineage in self.lineages:
            for stim in lineage.stimuli:
                stim.response_vector = self.db_util.read_responses_for(stim.id)
                stim.response_rate = self.db_util.read_driving_response(stim.id)

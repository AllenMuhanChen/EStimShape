from __future__ import annotations

from mysql.connector import DatabaseError

from intan.responses import ResponseParser
from newga.multi_ga_db_util import MultiGaDbUtil
from src.newga.ga_classes import Regime, Lineage
from util import time_util


class LineageDistributor:

    def distribute(self, name) -> {Lineage: int}:
        pass


class GeneticAlgorithm:

    def __init__(self, name: str, regimes: [Regime], db_util: MultiGaDbUtil, trials_per_generation: int,
                 lineage_distributor: LineageDistributor, response_parser: ResponseParser):
        self.name = name
        self.regimes = regimes
        self.db_util = db_util
        self.trials_per_generation = trials_per_generation
        self.lineage_distributor = lineage_distributor
        self.response_parser = response_parser

        self.gen_id: int = 0
        self.lineages: list[Lineage] = []

    def run(self):
        self.gen_id = self._read_gen_id()
        self.gen_id += 1

        if self.gen_id == 1:
            self._run_first_generation()
        elif self.gen_id > 1:
            self.response_parser.parse(self.name)
            # TODO: update lineages with new responses in database
            self._run_next_generation()
        else:
            raise ValueError("gen_id must be >= 1")

        self._write_lineages_to_db()

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

    def _write_lineages_to_db(self) -> None:
        # Write lineages
        for lineage in self.lineages:
            lineage_data = ""
            self.db_util.write_lineage_ga_info(lineage.id, lineage.tree.to_xml(), lineage_data)

        # Write stimuli
        for lineage in self.lineages:
            for stim in lineage.stimuli:
                self.db_util.write_stim_ga_info(stim.id, stim.parent.id, self.name, lineage.gen_id, lineage.id,
                                                stim.mutation_type)

        # Update generations
        self.db_util.update_ready_gas_and_generations_info(self.name, self.gen_id)


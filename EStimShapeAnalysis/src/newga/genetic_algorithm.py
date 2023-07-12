from newga.multi_ga_db_util import MultiGaDbUtil
from src.newga.ga_classes import Regime, Lineage
from util import time_util
from util.connection import Connection


class LineageDistributor:

    def distribute(self, name) -> {Lineage: int}:
        pass


class GeneticAlgorithm:
    def __init__(self, name: str, regimes: [Regime], db_util: MultiGaDbUtil, trials_per_generation: int,
                 lineage_distributor: LineageDistributor):
        self.name = name
        self.regimes = regimes
        self.db_util = db_util
        self.trials_per_generation = trials_per_generation
        self.lineage_distributor = lineage_distributor

        self.lineages = []

    def run(self):
        if self.is_first_generation():
            self.run_first_generation()
        else:
            self.run_next_generation()

        self.write_lineages_to_db()

    def is_first_generation(self):
        gen_id_for_ga = self.db_util.read_ready_gas_and_generations_info()
        ready_gen = gen_id_for_ga[self.name]
        if ready_gen == 0:
            return True
        else:
            return False

    def run_first_generation(self):
        # Initialize lineages
        for trial in range(self.trials_per_generation):
            # generate id
            founder_id = time_util.now()
            self.lineages.append(Lineage(founder_id, self.regimes))

        # Run lineages
        for lineage in self.lineages:
            lineage.generate_new_batch()
            lineage.regime_transition()

    def run_next_generation(self):
        num_trials_for_lineages = self.lineage_distributor.distribute(self.name)
        for lineage, num_trials in num_trials_for_lineages.items():
            lineage.generate_new_batch(num_trials)
            lineage.regime_transition()

    def write_lineages_to_db(self):
        pass

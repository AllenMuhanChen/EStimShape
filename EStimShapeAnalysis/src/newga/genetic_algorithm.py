from src.newga.ga_classes import Regime
from util.connection import Connection


class GeneticAlgorithm:
    def __init__(self, name: str, regimes: [Regime], connection: Connection):
        self.name = name
        self.regimes = regimes
        self.connection = connection

    def run(self):
        if self.is_first_generation():
            self.run_first_generation()
        else:
            self.run_next_generation()

    def is_first_generation(self):
        self.connection.execute("SELECT COUNT(*) FROM ga WHERE name = %s", (self.name,))

    def run_first_generation(self):
        pass

    def run_next_generation(self):
        pass

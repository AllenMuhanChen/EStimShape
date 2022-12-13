from src.compile.trial_collector import TrialCollector
from src.util.time_util import When


class DataAnalysisStep:
    def __init__(self, next_step=None):
        self.next_step = next_step

    def execute(self, data):
        data = self.analyze(data)
        if self.next_step:
            return self.next_step.execute(data)
        return data
    def analyze(self,data):
        return data
class TrialCompileStep(DataAnalysisStep):
    def analyze(self, when:When):





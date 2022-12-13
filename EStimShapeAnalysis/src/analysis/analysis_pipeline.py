class DataAnalysisStep:
    def __init__(self, next_step=None):
        self.next_step = next_step

    def execute(self, data):
        if self.next_step:
            return self.next_step.execute(data)
        return data




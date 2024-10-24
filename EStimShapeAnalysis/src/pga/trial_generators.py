import os
import subprocess
from typing import Protocol


class TrialGenerator(Protocol):
    """
    Protocol for trial generators.
    """

    def generate_trials(self, *, experiment_id: int, generation: int) -> int:
        pass


class AlexNetGAJarTrialGenerator(TrialGenerator):
    r = 255
    g = 255
    b = 255

    def __init__(self, java_output_dir: str, allen_dist: str) -> None:
        super().__init__()
        self.java_output_dir = java_output_dir
        self.allen_dist = allen_dist

    def generate_trials(self, *, experiment_id: int, generation: int):
        output_file = os.path.join(self.java_output_dir,
                                   f"experiment_{experiment_id}_generation_{generation}.txt")
        trial_generator_path = os.path.join(self.allen_dist, "AlexNetGAGenerator.jar")
        trial_generator_command = f"java -jar {trial_generator_path} {self.r} {self.g} {self.b}"

        with open(output_file, "w") as file:
            result = subprocess.run(trial_generator_command, shell=True, stdout=file, stderr=subprocess.STDOUT,
                                    text=True)
        return result.returncode

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b


class GAJarTrialGenerator(TrialGenerator):
    r = 255
    g = 255
    b = 255

    def __init__(self, java_output_dir: str, allen_dist: str) -> None:
        super().__init__()
        self.java_output_dir = java_output_dir
        self.allen_dist = allen_dist

    def generate_trials(self, *, experiment_id: int, generation: int):
        output_file = os.path.join(self.java_output_dir, f"experiment_{experiment_id}_generation_{generation}.txt")
        trial_generator_path = os.path.join(self.allen_dist, "GAGenerator.jar")
        trial_generator_command = f"java -jar {trial_generator_path} {self.r} {self.g} {self.b}"

        with open(output_file, "w") as file:
            result = subprocess.run(trial_generator_command, shell=True, stdout=file, stderr=subprocess.STDOUT,
                                    text=True)
        return result.returncode

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

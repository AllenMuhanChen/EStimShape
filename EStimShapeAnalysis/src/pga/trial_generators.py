import os
import subprocess

from src.startup import config
from typing import Protocol


class TrialGenerator(Protocol):
    """
    Protocol for trial generators.
    """
    def generate_trials(self, *, experiment_id: int, generation: int) -> int:
        pass


class GAJarTrialGenerator(TrialGenerator):
    r = 0
    g = 0
    b = 0

    def generate_trials(self, *, experiment_id: int, generation: int):
        def prompt_rgb_values():
            while True:
                rgb_input = input("Please enter RGB values in the format R,G,B (each between 0 and 255): ")
                try:
                    self.r, self.g, self.b = map(int, rgb_input.split(','))
                    if all(0 <= value <= 255 for value in [self.r, self.g, self.b]):
                        return self.r, self.g, self.b
                    else:
                        print("Values must be between 0 and 255. Please try again.")
                except ValueError:
                    print("Invalid format. Please ensure you enter three comma-separated numbers.")

        prompt_rgb_values()

        output_file = os.path.join(config.java_output_dir, f"experiment_{experiment_id}_generation_{generation}.txt")
        # TODO change jar to real jar
        trial_generator_path = os.path.join(config.allen_dist, "GAGenerator.jar")
        trial_generator_command = f"java -jar {trial_generator_path} {self.r} {self.g} {self.b}"

        with open(output_file, "w") as file:
            result = subprocess.run(trial_generator_command, shell=True, stdout=file, stderr=subprocess.STDOUT,
                                    text=True)
        return result.returncode

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

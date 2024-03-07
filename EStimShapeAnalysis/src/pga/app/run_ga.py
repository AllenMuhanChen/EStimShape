import os
import subprocess

from pga.app import config
from pga.config.twod_threed_config import TwoDThreeDGAConfig


def main():
    ga = config.ga_config.make_genetic_algorithm()
    ga.run()
    experiment_id = ga.experiment_id
    gen_id = ga.gen_id
    run_trial_generator(experiment_id, gen_id)


def run_trial_generator(experiment_id: int, generation: int):
    output_file = os.path.join(config.java_output_dir, f"experiment_{experiment_id}_generation_{generation}.txt")
    # TODO change jar to real jar
    trial_generator_path = os.path.join(config.allen_dist, "MockNewGATrialGenerator.jar")
    trial_generator_command = f"java -jar {trial_generator_path}"

    with open(output_file, "w") as file:
        result = subprocess.run(trial_generator_command, shell=True, stdout=file, stderr=subprocess.STDOUT, text=True)
    return result.returncode


if __name__ == "__main__":
    main()

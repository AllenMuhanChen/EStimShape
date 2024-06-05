import os
import subprocess

from src.startup import config


def main(r, g, b):
    # r, g, b = prompt_rgb_values()
    ga = config.ga_config.make_genetic_algorithm()
    ga.run()
    experiment_id = ga.experiment_id
    gen_id = ga.gen_id
    run_trial_generator(experiment_id, gen_id, r, g, b)


def prompt_rgb_values():
    while True:
        rgb_input = input("Please enter RGB values in the format R,G,B (each between 0 and 255): ")
        try:
            r, g, b = map(int, rgb_input.split(','))
            if all(0 <= value <= 255 for value in [r, g, b]):
                return r, g, b
            else:
                print("Values must be between 0 and 255. Please try again.")
        except ValueError:
            print("Invalid format. Please ensure you enter three comma-separated numbers.")


def run_trial_generator(experiment_id: int, generation: int, r: int, g: int, b: int):
    output_file = os.path.join(config.java_output_dir, f"experiment_{experiment_id}_generation_{generation}.txt")
    # TODO change jar to real jar
    trial_generator_path = os.path.join(config.allen_dist, "GAGenerator.jar")
    trial_generator_command = f"java -jar {trial_generator_path} {r} {g} {b}"

    with open(output_file, "w") as file:
        result = subprocess.run(trial_generator_command, shell=True, stdout=file, stderr=subprocess.STDOUT, text=True)
    return result.returncode


if __name__ == "__main__":
    main(255, 0, 0)

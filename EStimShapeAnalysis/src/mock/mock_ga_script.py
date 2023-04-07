from __future__ import annotations

import os
import subprocess
from time import sleep

from src.mock import mock_ga_responses
from src.util.connection import Connection

allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
xper_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/xper"

def main():
    num_generations = 8
    # start_experiment()
    ga_loop(num_generations)


def start_experiment():
    print("Starting AcqServer")
    try:
        acq_server_path = os.path.join(xper_dist, "acq_server.jar")
        acq_server_command = f"java -jar {acq_server_path}"
        subprocess.Popen(acq_server_command, shell=True)
    except Exception as e:
        print("AcqServer already running")

    print("Starting experiment console")
    console_path = os.path.join(allen_dist, "MockConsole.jar")
    console_command = f"java -jar {console_path}"
    subprocess.Popen(console_command, shell=True)

    print("Starting experiment")
    experiment_path = os.path.join(allen_dist, "MockExperiment.jar")
    experiment_command = f"java -jar {experiment_path}"
    subprocess.Popen(experiment_command, shell=True)


def ga_loop(num_generations):
    for generation in range(num_generations):
        run_trial_generator()
        sleep(5)
        mock_ga_responses.main()
        print(f"Generation {generation} responses mocked")


def run_trial_generator():
    output_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/tree_graph"
    output_file = os.path.join(output_dir, "output.txt")

    trial_generator_path = os.path.join(allen_dist, "MockNewGATrialGenerator.jar")
    trial_generator_command = f"java -jar {trial_generator_path}"

    with open(output_file, "w") as file:
        result = subprocess.run(trial_generator_command, shell=True, stdout=file, stderr=subprocess.STDOUT, text=True)
    return result.returncode

# def run_trial_generator():
#     trial_generator_path = os.path.join(allen_dist, "MockNewGATrialGenerator.jar")
#     trial_generator_command = f"java -jar {trial_generator_path}"
#     process = subprocess.Popen(trial_generator_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     while True:
#         output = process.stdout.readline().decode().strip()
#         error = process.stderr.readline().decode().strip()
#
#         # If the output and error streams are closed and there's no more output to read, break out of the loop
#         if process.poll() is not None and output == '' and error == '':
#             break
#
#         # If there is output or error to print, print it
#         if output:
#             print(output)
#         if error:
#             print(error)
#
#     return process.poll()


if __name__ == "__main__":
    main()

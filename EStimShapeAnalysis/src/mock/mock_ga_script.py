from __future__ import annotations

import os
import subprocess
from time import sleep

from src.mock import mock_ga_responses, mock_rwa_analysis, mock_rwa_plot, mock_tree_graph
from src.util.connection import Connection

allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
xper_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/xper"
conn = Connection("allen_estimshape_dev_221110")


def main():
    num_generations = 10

    ga_loop()

    mock_rwa_analysis.main()
    mock_rwa_plot.main()
    mock_tree_graph.main()


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


def ga_loop():
    generation = 1
    num_complete_lineages = 0
    while float(num_complete_lineages) < 1:
        print(f"Number of complete lineages: {num_complete_lineages}")
        run_trial_generator()
        print(f"Highest regime score so far: {get_highest_regime_score()}")
        sleep(5)
        mock_ga_responses.main()
        print(f"Generation {generation} responses mocked")
        generation += 1
        num_complete_lineages = number_of_complete_lineages()


def get_highest_regime_score():
    try:
        conn.execute("SELECT MAX(regime_score) FROM LineageGaInfo")
        highest_regime_score = conn.fetch_one()
        return float(highest_regime_score)
    except:
        return 0.0


def number_of_complete_lineages():
    conn.execute("SELECT COUNT(*) FROM LineageGaInfo WHERE regime_score = 4.0")
    num_complete_lineages = conn.fetch_one()
    return float(num_complete_lineages)


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

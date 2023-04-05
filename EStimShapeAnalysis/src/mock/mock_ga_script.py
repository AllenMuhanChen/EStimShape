from __future__ import annotations

import os
import subprocess
from time import sleep

from src.mock import mock_ga_responses
from src.util.connection import Connection

allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
xper_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/xper"

def main():
    num_generations = 5
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
        if run_trial_generator()==0:
            print(f"Generation {generation} generation complete")
        else:
            print(f"Generation {generation} failed")
            break
        sleep(5)
        mock_ga_responses.main()
        print(f"Generation {generation} responses mocked")



def run_trial_generator():
    trial_generator_path = os.path.join(allen_dist, "MockNewGATrialGenerator.jar")
    trial_generator_command = f"java -jar {trial_generator_path}"
    result = subprocess.run(trial_generator_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode


if __name__ == "__main__":
    main()

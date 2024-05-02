import os

import jsonpickle
from matplotlib import pyplot as plt

from analysis.ga.rwa import get_next
from clat.util.connection import Connection
from pga.app import config
from pga.mock.mock_rwa_plot import plot_shaft_rwa_1d, plot_termination_rwa_1d, plot_junction_rwa_1d
from pga.mock.plot_rwa_top_n import plot_top_n_stimuli_comp_maps, plot_top_n_stimuli_on_shaft, find_distances_to_peak, \
    plot_top_n_stimuli_on_termination, plot_top_n_junctions_on_fig, print_top_stim_and_comp_ids


def main():
    conn = Connection(config.ga_database)

    experiment_id = input("Enter the experiment id (enter nothing for most recent):")
    if experiment_id == "":
        experiment_id = config.ga_config.db_util.read_current_experiment_id(config.ga_name)
    else:
        experiment_id = int(experiment_id)

    n = int(input("Enter the number of stimuli to plot:"))
    image_path = config.image_path

    shaft_rwa_path = os.path.join(config.rwa_output_dir, f"{experiment_id}_shaft_rwa.json")
    shaft_rwa = jsonpickle.decode(
        open(shaft_rwa_path, "r").read())
    fig_shaft = plot_shaft_rwa_1d(get_next(shaft_rwa))
    plot_top_n_stimuli_on_shaft(n, fig_shaft, shaft_rwa, conn)
    distances_to_shaft_peak = find_distances_to_peak(shaft_rwa, n, conn, 'shaft')
    print("distances SHAFT: " + str(distances_to_shaft_peak))

    plt.suptitle("Combined SHAFT RWA")

    termination_rwa_path = os.path.join(config.rwa_output_dir, f"{experiment_id}_termination_rwa.json")
    termination_rwa = jsonpickle.decode(
        open("%s" % termination_rwa_path, "r").read())
    fig_termination = plot_termination_rwa_1d(get_next(termination_rwa))
    plot_top_n_stimuli_on_termination(n, fig_termination, termination_rwa, conn)
    distances_to_termination_peak = find_distances_to_peak(termination_rwa, n, conn, 'termination')
    print("distances TERMINATION: " + str(distances_to_termination_peak))
    plt.suptitle("Combined TERMINATION RWA")

    junction_rwa_path = os.path.join(config.rwa_output_dir, f"{experiment_id}_junction_rwa.json")
    junction_rwa = jsonpickle.decode(
        open(junction_rwa_path, "r").read())
    fig = plot_junction_rwa_1d(get_next(junction_rwa))
    plot_top_n_junctions_on_fig(n, fig, junction_rwa, conn)
    distances_to_junction_peak = find_distances_to_peak(junction_rwa, n, conn, 'junction')
    print("distances JUNCTION: " + str(distances_to_junction_peak))
    plt.suptitle("Combined JUNCTION RWA")

    print_top_stim_and_comp_ids(experiment_id, conn, distances_to_junction_peak, distances_to_shaft_peak,
                                distances_to_termination_peak, n)

    plot_top_n_stimuli_comp_maps(experiment_id, n, conn, image_path)
    plt.show()


if __name__ == "__main__":
    main()
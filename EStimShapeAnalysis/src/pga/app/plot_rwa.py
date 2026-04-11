import os
import pickle

from matplotlib import pyplot as plt

from src.analysis.ga.rwa import get_next
from src.analysis.ga.rwa_prediction import compute_predictions, plot_real_vs_predicted
from clat.util.connection import Connection
from src.startup import context
from src.pga.mock.mock_rwa_plot import plot_shaft_rwa_1d, plot_termination_rwa_1d, plot_junction_rwa_1d
from src.pga.mock.plot_rwa_top_n import plot_top_n_stimuli_comp_maps, plot_top_n_stimuli_on_shaft, find_distances_to_peak, \
    plot_top_n_stimuli_on_termination, plot_top_n_junctions_on_fig, print_top_stim_and_comp_ids


def main():
    conn = Connection(context.ga_database)

    experiment_id = input("Enter the experiment id (enter nothing for most recent):")
    if experiment_id == "":
        experiment_id = context.ga_config.db_util.read_current_experiment_id(context.ga_name)
    else:
        experiment_id = int(experiment_id)

    num_stimuli_to_plot_on_rwa = int(input("Enter the number of stimuli to plot on RWA:"))
    num_stimuli_to_show_comp_map = int(input("Enter the number of stimuli to show composition maps:"))
    image_path = context.image_path

    shaft_rwa_path = os.path.join(context.rwa_output_dir, f"{experiment_id}_shaft_rwa.pkl")
    with open(shaft_rwa_path, "rb") as f:
        shaft_rwa = pickle.load(f)
    fig_shaft = plot_shaft_rwa_1d(get_next(shaft_rwa))
    plot_top_n_stimuli_on_shaft(num_stimuli_to_plot_on_rwa, fig_shaft, shaft_rwa, conn)
    distances_to_shaft_peak = find_distances_to_peak(shaft_rwa, num_stimuli_to_plot_on_rwa, conn, 'shaft')
    print("distances SHAFT: " + str(distances_to_shaft_peak))

    plt.suptitle("Combined SHAFT RWA")

    termination_rwa_path = os.path.join(context.rwa_output_dir, f"{experiment_id}_termination_rwa.pkl")
    with open(termination_rwa_path, "rb") as f:
        termination_rwa = pickle.load(f)
    fig_termination = plot_termination_rwa_1d(get_next(termination_rwa))
    plot_top_n_stimuli_on_termination(num_stimuli_to_plot_on_rwa, fig_termination, termination_rwa, conn)
    distances_to_termination_peak = find_distances_to_peak(termination_rwa, num_stimuli_to_plot_on_rwa, conn, 'termination')
    print("distances TERMINATION: " + str(distances_to_termination_peak))
    plt.suptitle("Combined TERMINATION RWA")

    junction_rwa_path = os.path.join(context.rwa_output_dir, f"{experiment_id}_junction_rwa.pkl")
    with open(junction_rwa_path, "rb") as f:
        junction_rwa = pickle.load(f)
    fig = plot_junction_rwa_1d(get_next(junction_rwa))
    plot_top_n_junctions_on_fig(num_stimuli_to_plot_on_rwa, fig, junction_rwa, conn)
    distances_to_junction_peak = find_distances_to_peak(junction_rwa, num_stimuli_to_plot_on_rwa, conn, 'junction')
    print("distances JUNCTION: " + str(distances_to_junction_peak))
    plt.suptitle("Combined JUNCTION RWA")

    print_top_stim_and_comp_ids(experiment_id, conn, distances_to_junction_peak, distances_to_shaft_peak,
                                distances_to_termination_peak, num_stimuli_to_plot_on_rwa)

    plot_top_n_stimuli_comp_maps(experiment_id, num_stimuli_to_show_comp_map, conn, image_path)

    # ---- Real vs Predicted scatter ----
    data_path = os.path.join(context.rwa_output_dir, f"{experiment_id}_data.pkl")
    if os.path.exists(data_path):
        with open(data_path, "rb") as f:
            data = pickle.load(f)

        fig_scatter, axes = plt.subplots(1, 3, figsize=(15, 5))
        for ax, (rwa_mat, col, label) in zip(axes, [
            (shaft_rwa,       "Shaft",       "Shaft"),
            (termination_rwa, "Termination", "Termination"),
            (junction_rwa,    "Junction",    "Junction"),
        ]):
            preds = compute_predictions(rwa_mat, data[col])
            plot_real_vs_predicted(data["Response-1"], preds, title=label, ax=ax)

        fig_scatter.suptitle(
            f"RWA Prediction Correlation — Experiment {experiment_id}",
            fontsize=13, fontweight='bold',
        )
        plt.tight_layout()
    else:
        print(f"No data file found at {data_path} — re-run run_rwa.py to generate it.")

    plt.show()


if __name__ == "__main__":
    main()
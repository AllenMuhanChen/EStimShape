import os
from matplotlib import pyplot as plt
from clat.util.connection import Connection

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis
from src.analysis.shuffle.shuffle_analysis import ShuffleAnalysis
from src.sort.window_sort.export_sort_to_repository import export_sorted_spikes


def get_units_for_session(session_name: str) -> list[str]:
    """
    Query the data repository to find all unique units in WindowSortedResponses for a given session.

    Args:
        session_name: The session identifier to search for

    Returns:
        List of unique unit names found in WindowSortedResponses for this session
    """
    conn = Connection("allen_data_repository")

    query = """
            SELECT DISTINCT wsr.unit_id
            FROM Sessions s
                     JOIN Experiments e ON s.session_id = e.session_id
                     JOIN StimExperimentMapping sem ON e.experiment_id = sem.experiment_id
                     JOIN TaskStimMapping tsm ON sem.stim_id = tsm.stim_id
                     JOIN WindowSortedResponses wsr ON tsm.task_id = wsr.task_id
            WHERE s.session_id = %s
            ORDER BY wsr.unit_id \
            """

    conn.execute(query, (session_name,))
    results = conn.fetch_all()

    # Extract unit names from tuples
    units = [row[0] for row in results]

    print(f"Found {len(units)} units for session {session_name}:")
    for unit in units:
        print(f"  {unit}")

    return units


def main():
    analyses = [
        # IsogaborAnalysis(),
        PlotTopNAnalysis(),
        # SideTestAnalysis(),
        # LightnessAnalysis(),
        # MixedGaborsAnalysis(),
        # ShuffleAnalysis()
    ]

    # INPUTS #
    session_name = '251001_1'
    label = None
    new_spikes = False
    ##########

    save_path = f"/home/connorlab/Documents/EStimShape/allen_sort_{session_name}/plots"
    # if save_path is None: make it
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    if new_spikes:
        export_sorted_spikes(session_name, label)

    # Get all units for this session
    units = get_units_for_session(session_name)

    if not units:
        print(f"No units found for session {session_name}")
        return

    # Run analysis for each unit
    for unit in units:
        if label:
            labeled_unit = f"{label}_{unit}"
        else:
            labeled_unit = unit

        print(f"\n=== Running analyses for unit: {labeled_unit} ===")

        for analysis in analyses:
            try:
                analysis.run(session_name, "sorted", labeled_unit)
            except Exception as e:
                print(f"Error running {analysis.__class__.__name__} for unit {labeled_unit}: {e}")
                continue

    plt.show()


if __name__ == "__main__":
    main()
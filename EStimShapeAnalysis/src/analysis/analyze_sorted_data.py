import os
from typing import List, Tuple
from matplotlib import pyplot as plt
from clat.util.connection import Connection
from src.analysis.ga.plot_generations import PlotGenerationsAnalysis

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
            ORDER BY wsr.unit_id
            """

    conn.execute(query, (session_name,))
    results = conn.fetch_all()

    # Extract unit names from tuples
    units = [row[0] for row in results]

    print(f"Found {len(units)} units for session {session_name}:")
    for unit in units:
        print(f"  {unit}")

    return units


def fetch_all_sessions() -> List[Tuple[str]]:
    """Fetch all session IDs from the database."""
    conn = Connection("allen_data_repository")
    query = "SELECT session_id FROM Sessions"
    conn.execute(query)
    return conn.fetch_all()


def main():
    # ============ CONFIGURATION ============
    # Set to specific session ID or None for all sessions
    session_name = "251008_0"

    # Set to specific unit or None for all units in session
    specific_unit = None  # e.g., 'A-013_Unit 1' or None for all units

    # Label to prepend to unit names (None for no label)
    label = None

    # Whether to export new sorted spikes before analysis
    new_spikes = True

    # Which analyses to run
    analyses = [
        IsogaborAnalysis(),
        PlotTopNAnalysis(),
        # PlotGenerationsAnalysis(),
        SideTestAnalysis(),
        # LightnessAnalysis(),
        # MixedGaborsAnalysis(),
        # ShuffleAnalysis()
    ]
    # =======================================

    # Determine which sessions to process
    if session_name:
        sessions_to_process = [(session_name,)]
        print(f"Processing single session: {session_name}")
    else:
        sessions_to_process = fetch_all_sessions()
        print(f"Processing all sessions: found {len(sessions_to_process)} sessions")

    # Process each session
    for (session_id,) in sessions_to_process:
        print(f"\n{'=' * 60}")
        print(f"Processing session: {session_id}")
        print(f"{'=' * 60}")

        # Create save path
        save_path = f"/home/connorlab/Documents/EStimShape/allen_sort_{session_id}/plots"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # Export new sorted spikes if requested
        if new_spikes:
            print(f"Exporting sorted spikes for session {session_id}")
            export_sorted_spikes(session_id, label)

        # Determine which units to process
        if specific_unit:
            units = [specific_unit]
            print(f"Processing specific unit: {specific_unit}")
        else:
            units = get_units_for_session(session_id)
            if not units:
                print(f"No units found for session {session_id}, skipping")
                continue

        # Process each unit
        for unit in units:
            if label:
                labeled_unit = f"{label}_{unit}"
            else:
                labeled_unit = unit

            print(f"\n=== Running analyses for unit: {labeled_unit} ===")

            # Run each analysis
            for analysis in analyses:
                analysis_name = analysis.__class__.__name__
                try:
                    print(f"  Running {analysis_name}...")
                    analysis.run(session_id, "sorted", labeled_unit)
                    print(f"  ✓ {analysis_name} completed")
                except Exception as e:
                    print(f"  ✗ Error in {analysis_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

    print(f"\n{'=' * 60}")
    print("All processing complete")
    print(f"{'=' * 60}")

    plt.show()


if __name__ == "__main__":
    main()
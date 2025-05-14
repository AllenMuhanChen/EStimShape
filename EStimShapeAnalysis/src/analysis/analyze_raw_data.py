from typing import List, Tuple
from clat.util.connection import Connection
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis
from src.repository.good_channels import read_good_channels, read_cluster_channels


def main():
    # Initialize analysis modules
    analyses = [
        IsogaborAnalysis(),
        PlotTopNAnalysis(),
        SideTestAnalysis(),
        LightnessAnalysis(),
        MixedGaborsAnalysis(),
    ]

    # Ask for session ID (empty for all sessions)
    session_id = input("Enter session ID (leave empty for all sessions): ").strip()

    if session_id:
        # User specified a session
        sessions_to_process = [(session_id,)]

        # Ask for channel (empty for all cluster channels)
        channel = input("Enter channel (leave empty for all cluster channels): ").strip()

        if channel:
            # User specified both session and channel
            channels_map = {session_id: [channel]}
        else:
            # User specified session but not channel
            channels = read_cluster_channels(session_id)
            if not channels:
                raise ValueError(f"No cluster channels found for session {session_id}.")
            channels_map = {session_id: channels}
    else:
        # Process all sessions
        print("Fetching all sessions...")
        sessions_to_process = fetch_session_ids()
        print(f"Found {len(sessions_to_process)} sessions")

        # Use cluster channels for all sessions
        channels_map = {}
        for (session_id,) in sessions_to_process:
            channels = read_cluster_channels(session_id)
            if channels:
                channels_map[session_id] = channels
            else:
                print(f"No cluster channels found for session {session_id}. Using default channel.")
                channels_map[session_id] = ["A-011"]

    # Process sessions
    for (session_id,) in sessions_to_process:
        if session_id not in channels_map or not channels_map[session_id]:
            print(f"No channels configured for session {session_id}. Skipping.")
            continue

        channels = channels_map[session_id]
        print(f"\nProcessing session {session_id} with {len(channels)} channels:")
        for channel in channels:
            print(f"  - {channel}")

        # Run all analyses for this session
        for analysis in analyses:
            for channel in channels:
                print(f"Running {analysis.__class__.__name__} for session {session_id}, channel {channel}")
                try:
                    analysis.run(session_id=session_id, data_type="raw", channel=channel)
                except Exception as e:
                    print(f"Error running {analysis.__class__.__name__} for session {session_id}, channel {channel}: {e}")
                    # print full traceback
                    import traceback
                    traceback.print_exc()


def fetch_session_ids() -> List[Tuple[str]]:
    """Fetch all session IDs from the database."""
    conn = Connection("allen_data_repository")
    query = "SELECT session_id FROM Sessions"
    conn.execute(query)
    return conn.fetch_all()


if __name__ == "__main__":
    main()

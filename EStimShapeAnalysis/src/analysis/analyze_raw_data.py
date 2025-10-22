from typing import List, Tuple, Dict
from clat.util.connection import Connection
from src.analysis.ga.plot_generations import PlotGenerationsAnalysis
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis, SolidPreferenceIndexAnalysis

from src.analysis.ga.stimulus_sensitivity_test import StimulusSelectivityTest, StimulusSelectivityAnalysis
from src.analysis.isogabor.isochromatic_luminant_score import IsoChromaticLuminantScoreAnalysis

from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis, IsochromaticIndexAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis
from src.analysis.shuffle.shuffle_analysis import ShuffleAnalysis
from src.repository.good_channels import read_cluster_channels


def get_all_channels() -> List[str]:
    """Generate list of all possible channels A-000 through A-031."""
    return [f"A-{i:03d}" for i in range(32)]


def get_channel_selection() -> str:
    """Ask user for channel selection mode."""
    print("\nChannel selection:")
    print("1. Specific channel")
    print("2. Cluster channels only")
    print("3. All channels (A-000 to A-031)")

    while True:
        choice = input("Enter choice (1-3): ").strip()
        if choice in ['1', '2', '3']:
            return choice
        print("Invalid choice. Please enter 1, 2, or 3.")


def get_channels_for_session(session_id: str, channel_mode: str, specific_channel: str = None) -> List[str]:
    """Get channels for a session based on the mode."""
    if channel_mode == '1':  # Specific channel
        if specific_channel:
            return [specific_channel]
        channel = input(f"Enter channel for session {session_id}: ").strip()
        return [channel] if channel else []

    elif channel_mode == '2':  # Cluster channels
        channels = read_cluster_channels(session_id)
        if not channels:
            print(f"No cluster channels found for session {session_id}.")
        return channels

    else:  # All channels (mode == '3')
        return get_all_channels()


def fetch_session_ids() -> List[str]:
    """Fetch all session IDs from the database."""
    conn = Connection("allen_data_repository")
    query = "SELECT session_id FROM Sessions"
    conn.execute(query)
    return [session_id for (session_id,) in conn.fetch_all()]


def build_sessions_and_channels() -> Dict[str, List[str]]:
    """Build a map of sessions to channels based on user input."""
    # Ask for session selection
    session_id = input("Enter session ID (leave empty for all sessions): ").strip()

    if session_id:
        # Single session
        sessions = [session_id]
    else:
        # All sessions
        print("Fetching all sessions...")
        sessions = fetch_session_ids()
        print(f"Found {len(sessions)} sessions")

    # Ask for channel selection mode
    channel_mode = get_channel_selection()

    # Get specific channel if needed
    specific_channel = None
    if channel_mode == '1' and len(sessions) == 1:
        specific_channel = input("Enter channel: ").strip()

    # Build channels map
    channels_map = {}
    for session_id in sessions:
        channels = get_channels_for_session(session_id, channel_mode, specific_channel)
        if channels:
            channels_map[session_id] = channels
        else:
            print(f"Warning: No channels found for session {session_id}. Skipping.")

    return channels_map


def run_analyses(channels_map: Dict[str, List[str]], analyses: List):
    """Run all analyses for all sessions and channels."""
    for session_id, channels in channels_map.items():
        print(f"\n{'=' * 60}")
        print(f"Processing session {session_id} with {len(channels)} channels:")
        for channel in channels:
            print(f"  - {channel}")
        print('=' * 60)

        for analysis in analyses:
            for channel in channels:
                print(f"\nRunning {analysis.__class__.__name__} for session {session_id}, channel {channel}")
                try:
                    analysis.run(session_id=session_id, data_type="raw", channel=channel)
                except Exception as e:
                    print(f"Error running {analysis.__class__.__name__}: {e}")
                    import traceback
                    traceback.print_exc()


def main():
    # Initialize analysis modules
    analyses = [
        StimulusSelectivityAnalysis(),
        IsoChromaticLuminantScoreAnalysis(),
        IsochromaticIndexAnalysis(),
        SolidPreferenceIndexAnalysis(),
        # IsogaborAnalysis(),
        # PlotTopNAnalysis(),
        # SideTestAnalysis(),
        # LightnessAnalysis(),
        # MixedGaborsAnalysis(),
        # ShuffleAnalysis(),
        # PlotGenerationsAnalysis(),
    ]

    # Build session-to-channels mapping based on user input
    channels_map = build_sessions_and_channels()

    if not channels_map:
        print("No sessions or channels to process. Exiting.")
        return

    # Run analyses
    run_analyses(channels_map, analyses)

    print("\n" + "=" * 60)
    print("All analyses complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
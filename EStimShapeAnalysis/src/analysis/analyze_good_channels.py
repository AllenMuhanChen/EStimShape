from src.analysis.analyze_raw_data import fetch_session_ids
from src.analysis.ga.analyze_channels import FilterChannelsByGAAnalysis
from src.analysis.ga.plot_generations import PlotGenerationsAnalysis
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis
from src.analysis.shuffle.shuffle_analysis import ShuffleAnalysis
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context


def main():
    analyses = [
        IsogaborAnalysis(),
        # PlotTopNAnalysis(),
        # PlotGenerationsAnalysis(),
        SideTestAnalysis(),
        # LightnessAnalysis(),
        # MixedGaborsAnalysis(),
        # ShuffleAnalysis()
    ]

    # Ask for session ID (empty for all sessions)
    session_id = input("Enter session ID (leave empty for current session and 'all' for all sessions): ").strip()

    if session_id == "":
        # User specified a session
        session_id, _ = read_session_id_from_db_name(context.ga_database)
        good_channels = extract_good_channels(session_id)
        sessions_to_process = [(session_id,)]
        channels_map = {session_id: good_channels}

    elif session_id == "all":
        # Process all sessions
        print("Fetching all sessions...")
        sessions_to_process = fetch_session_ids()
        print(f"Found {len(sessions_to_process)} sessions")

        # Use cluster channels for all sessions
        channels_map = {}
        for (session_id,) in sessions_to_process:
            channels = extract_good_channels(session_id)
            channels_map[session_id] = channels
    else:
        good_channels = extract_good_channels(session_id)
        sessions_to_process = [(session_id,)]
        channels_map = {session_id: good_channels}


    for (session_id,) in sessions_to_process:
        if session_id not in channels_map or not channels_map[session_id]:
            print(f"No channels configured for session {session_id}. Skipping.")
            continue

        channels = channels_map[session_id]
        print(f"\nProcessing session {session_id} with {len(channels)} channels:")
        for channel in channels:
            print(f"  - {channel}")

        # Run all analyses for this session
        for channel in channels:
            for analysis in analyses:
                print(f"Running {analysis.__class__.__name__} for session {session_id}, channel {channel}")
                try:
                    analysis.run(session_id=session_id, data_type="raw", channel=channel)
                except Exception as e:
                    print(f"Error running {analysis.__class__.__name__} for session {session_id}, channel {channel}: {e}")
                    # print full traceback
                    # import traceback
                    # traceback.print_exc()

def extract_good_channels(session_id):
    channel_analysis = FilterChannelsByGAAnalysis()
    good_channels, mean_rates = channel_analysis.run(session_id, "raw", None, compiled_data=None)
    return good_channels, mean_rates


if __name__ == "__main__":
    main()
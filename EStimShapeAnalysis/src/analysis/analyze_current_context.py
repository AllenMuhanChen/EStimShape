from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import traceback

from src.analysis.ga.plot_generations import PlotGenerationsAnalysis
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis
from src.analysis.shuffle.shuffle_analysis import ShuffleAnalysis
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.startup import context


def run_analyses_for_channel(channel, session_id):
    """Run all analyses for a single channel.

    Creates fresh instances of all analysis objects to avoid shared state issues.
    """
    # Create fresh instances for this process - no shared state
    analyses = [
        IsogaborAnalysis(),
        PlotGenerationsAnalysis(),
        PlotTopNAnalysis(),
        SideTestAnalysis(),
        LightnessAnalysis(),
        MixedGaborsAnalysis(),
        ShuffleAnalysis(),
    ]

    results = []
    for analysis in analyses:
        analysis_name = analysis.__class__.__name__
        print(f"Running {analysis_name} for channel {channel}")
        try:
            compiled_data = analysis.compile()
            analysis.run(session_id=session_id, data_type="raw", channel=channel.value, compiled_data=compiled_data)
            results.append((channel, analysis_name, "Success", None))
        except Exception as e:
            error_msg = f"Error running {analysis_name} for session {session_id}, channel {channel}: {e}"
            print(error_msg)
            traceback.print_exc()
            results.append((channel, analysis_name, "Failed", str(e)))

    return results


def main():
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    channel_ids = context.ga_config.db_util.read_current_cluster("New3D")

    # Use max_workers to control number of parallel processes
    max_workers = max(1, cpu_count() - 1)
    print(f"Using {max_workers} worker processes")
    print(f"Processing {len(channel_ids)} channels with {7} analyses each")

    # Run analyses in parallel across channels
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs - each gets its own fresh analysis instances
        future_to_channel = {
            executor.submit(run_analyses_for_channel, channel, session_id): channel
            for channel in channel_ids
        }

        # Process completed jobs as they finish
        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                results = future.result()
                print(f"\n✓ Completed all analyses for channel {channel}")
                # Print any failures
                failures = [r for r in results if r[2] == "Failed"]
                if failures:
                    for ch, analysis, status, error in failures:
                        print(f"  ❌ {analysis}: {error}")
            except Exception as e:
                print(f"\n❌ Fatal error processing channel {channel}: {e}")
                traceback.print_exc()


if __name__ == '__main__':
    main()
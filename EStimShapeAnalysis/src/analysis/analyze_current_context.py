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


def main():
    analyses = [
        # IsogaborAnalysis(),
        PlotGenerationsAnalysis(),
        # PlotTopNAnalysis(),
        SideTestAnalysis(),
        # LightnessAnalysis(),
        # MixedGaborsAnalysis(),
        # ShuffleAnalysis(),
    ]

    session_id, _ = read_session_id_from_db_name(context.ga_database)
    channel_ids = context.ga_config.db_util.read_current_cluster("New3D")


    for analysis in analyses:
        for channel in channel_ids:
            print(f"Running {analysis.__class__.__name__} for channel {channel}")
            try:
                compiled_data = analysis.compile()
                analysis.run(session_id=session_id, data_type="raw", channel=channel, compiled_data=compiled_data)
            except Exception as e:
                print(f"Error running {analysis.__class__.__name__} for session {session_id}, channel {channel}: {e}")
                # print full traceback
                import traceback
                traceback.print_exc()


if __name__ == '__main__':
    main()



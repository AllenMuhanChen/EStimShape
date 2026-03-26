from src.analysis.analyze_raw_data import get_all_channels
from src.analysis.ga.ga_vector_analysis import GAResponseVectorAnalysis
from src.analysis.ga.lfp_analysis import LFPAnalysis
from src.analysis.ga.plot_generations import PlotGenerationsAnalysis
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis, SolidPreferenceIndexAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis, IsochromaticIndexAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis
from src.analysis.shuffle.shuffle_analysis import ShuffleAnalysis
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.startup import context


def main():
    channel_order = [7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
                     27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17]
    # BARE MINIMUM FOR PREFERENCE CLUSTER
    bare_minimum_for_preference_cluster = [
        IsochromaticIndexAnalysis(),
        GAResponseVectorAnalysis(),
        SolidPreferenceIndexAnalysis(),
    ]
    analyses = bare_minimum_for_preference_cluster

    # analyses.append(LFPAnalysis(channel_order=channel_order,
    #                             mode="iti"))




    session_id, _ = read_session_id_from_db_name(context.ga_database)
    # channel_ids = context.ga_config.db_util.read_current_cluster("New3D")

    channels = get_all_channels()
    for analysis in analyses:
        try:
            compiled_data = analysis.compile_and_export()
            analysis.run_on_channels(session_id=session_id,
                                     data_type="raw",
                                     channels=channels,
                                     compiled_data=compiled_data)
        except Exception as e:
            print(f"Error running {analysis.__class__.__name__} for session {session_id}, channel {channels}: {e}")
            # print full traceback
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()



import traceback

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis
from src.analysis.shuffle.shuffle_analysis import ShuffleAnalysis


def main():
    analyses = [
        # IsogaborAnalysis(),
        # PlotTopNAnalysis(),
        SideTestAnalysis(),
        # LightnessAnalysis(),
        # MixedGaborsAnalysis(),
        # ShuffleAnalysis()
    ]

    for analysis in analyses:
        try:
            analysis.compile_and_export()
        except Exception as e:
            print(f"Failed to compile analysis: {e}")
            traceback.print_exc()  # This prints the full stack trace

if __name__ == "__main__":
    main()



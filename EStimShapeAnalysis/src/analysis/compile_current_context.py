from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis




def main():
    analyses = [
        # IsogaborAnalysis(),
        PlotTopNAnalysis(),
        # SideTestAnalysis(),
        # LightnessAnalysis(),
        # MixedGaborsAnalysis(),
    ]

    for analysis in analyses:
        analysis.compile_and_export()




if __name__ == "__main__":
    main()



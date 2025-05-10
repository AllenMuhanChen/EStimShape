
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis


def main():
    analyses = [
        IsogaborAnalysis(),
        PlotTopNAnalysis(),
        SideTestAnalysis(),
        LightnessAnalysis(),
        MixedGaborsAnalysis(),
    ]
    "/home/r2_allen/Documents/EStimShape/allen_sort_250506_0/raw"
    session_id = "250506_0"
    channel = "A-020"
    for analysis in analyses:
        analysis.run(session_id=session_id, data_type="raw", channels=channel)




if __name__ == "__main__":
    main()



import os

from matplotlib import pyplot as plt

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.side_test import SideTestAnalysis
from src.analysis.isogabor.isogabor_raster_pipeline import IsogaborAnalysis
from src.analysis.isogabor.mixed_gabors_analysis import MixedGaborsAnalysis
from src.analysis.lightness.lightness_analysis import LightnessAnalysis

from src.sort.window_sort.export_sort_to_repository import export_sorted_spikes


def main():
    analyses = [
        IsogaborAnalysis(),
        PlotTopNAnalysis(),
        SideTestAnalysis(),
        LightnessAnalysis(),
        MixedGaborsAnalysis(),
    ]
    # INPUTS #
    session_name = '250507_0'
    unit = 'A-002_Unit 2'
    label = None
    new_spikes = False
    ##########
    save_path = f"/home/r2_allen/Documents/EStimShape/allen_sort_{session_name}/plots"
    # if save_path is None: make it
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    if label:
        unit = f"{label}_{unit}"

    if new_spikes:
        export_sorted_spikes(session_name, label)

    for analysis in analyses:
        analysis.run(session_name, "sorted", unit)

    plt.show()

if __name__ == "__main__":
    main()
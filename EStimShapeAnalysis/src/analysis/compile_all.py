from src.analysis.ga import plot_top_n, side_test
from src.analysis.isogabor import isogabor_raster_pipeline, mixed_gabors_analysis
from src.analysis.lightness import lightness_analysis

analyses = [isogabor_raster_pipeline, plot_top_n, lightness_analysis, mixed_gabors_analysis, side_test]


def main():
    for analysis in analyses:
        analysis.compile_and_export()


if __name__ == "__main__":
    main()



from src.pga.alexnet.alexnet_config import AlexNetExperimentGeneticAlgorithmConfig
from src.pga.alexnet.onnx_parser import UnitIdentifier, LayerType

ga_name = "New3D"
ga_database = "allen_alexnet_ga_exp_241101_0"
image_path = "/home/r2_allen/Documents/EStimShape/allen_alexnet_ga_exp_241101_0/stimuli/ga/pngs/"
java_output_dir = "/home/r2_allen/Documents/EStimShape/allen_alexnet_ga_exp_241101_0/java_output/"
rwa_output_dir = "/home/r2_allen/Documents/EStimShape/allen_alexnet_ga_exp_241101_0/rwa/"
ga_plots_dir = "/home/r2_allen/Documents/EStimShape/allen_alexnet_ga_exp_241101_0/plots/"

contrast_database = "allen_alexnet_contrast_exp_241101_0"
contrast_plots_dir = "/home/r2_allen/Documents/EStimShape/allen_alexnet_contrast_exp_241101_0/plots/"

lighting_database = "allen_alexnet_lighting_exp_241101_0"
lighting_plots_dir = "/home/r2_allen/Documents/EStimShape/allen_alexnet_lighting_exp_241101_0/plots/"

allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"



unit = UnitIdentifier(layer=LayerType.CONV3, unit=109, x=7, y=7)

try:
    ga_config = AlexNetExperimentGeneticAlgorithmConfig(database=ga_database,
                                                        java_output_dir=java_output_dir,
                                                        allen_dist_dir=allen_dist,
                                                        unit=unit)
except Exception:
    print("Error creating GA config")


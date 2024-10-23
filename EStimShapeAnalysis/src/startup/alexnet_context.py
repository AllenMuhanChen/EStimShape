from src.pga.alexnet.alexnet_config import AlexNetExperimentGeneticAlgorithmConfig
from src.pga.alexnet.onnx_parser import UnitIdentifier, LayerType

ga_name = "C31"
ga_database = "allen_alexnet_ga_dev_241021_1"
allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
image_path = f"/home/r2_allen/Documents/EStimShape/{ga_database}/stimuli/ga/pngs"
java_output_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}/java_output"
rwa_output_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}/rwa"

unit = UnitIdentifier(layer=LayerType.CONV3, unit=70, x=6, y=6)

ga_config = AlexNetExperimentGeneticAlgorithmConfig(database=ga_database,
                                                    java_output_dir=java_output_dir,
                                                    allen_dist_dir=allen_dist,
                                                    unit=unit)

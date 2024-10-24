from src.pga.alexnet.alexnet_config import AlexNetExperimentGeneticAlgorithmConfig
from src.pga.alexnet.onnx_parser import UnitIdentifier, LayerType

ga_name = "C31"
ga_database = "allen_alexnet_ga_test_241024_0"
allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
image_path = "/home/r2_allen/Documents/EStimShape/allen_alexnet_ga_test_241024_0/stimuli/ga/pngs"
java_output_dir = "/home/r2_allen/Documents/EStimShape/allen_alexnet_ga_test_241024_0/java_output"
rwa_output_dir = "/home/r2_allen/Documents/EStimShape/allen_alexnet_ga_test_241024_0/rwa"

unit = UnitIdentifier(layer=LayerType.CONV3, unit=134, x=6, y=6)

ga_config = AlexNetExperimentGeneticAlgorithmConfig(database=ga_database,
                                                    java_output_dir=java_output_dir,
                                                    allen_dist_dir=allen_dist,
                                                    unit=unit)

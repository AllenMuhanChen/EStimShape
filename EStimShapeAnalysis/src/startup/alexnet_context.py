from src.pga.alexnet.alexnet_config import AlexNetExperimentGeneticAlgorithmConfig

ga_name = "C31"
ga_database = "allen_ga_dev_241017_1"
allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
image_path = f"/home/r2_allen/Documents/EStimShape/{ga_database}/stimuli/ga/pngs"
java_output_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}/java_output"
rwa_output_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}/rwa"
ga_config = AlexNetExperimentGeneticAlgorithmConfig(database=ga_database,
                                                      base_intan_path=None,
                                                      java_output_dir=java_output_dir,
                                                      allen_dist_dir=allen_dist)
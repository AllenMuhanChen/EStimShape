from src.pga.config.twod_threed_config import TwoDThreeDGAConfig
from src.pga.mock.alexnet_mock_ga import FullAutoAlexNetMockGeneticAlgorithmConfig, \
    TrainingAlexNetMockGeneticAlgorithmConfig

ga_name = "New3D"
ga_database = "allen_estimshape_ga_train_240604"
nafc_database = "allen_estimshape_train_240604"
isogabor_database = "allen_isogabor_train_240604"
allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
image_path = "/home/r2_allen/Documents/EStimShape/allen_estimshape_ga_train_240604/stimuli/ga/pngs"
java_output_dir = "/home/r2_allen/Documents/EStimShape/allen_estimshape_ga_train_240604/java_output"
rwa_output_dir = "/home/r2_allen/Documents/EStimShape/allen_estimshape_ga_train_240604/rwa"
base_intan_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/allen_estimshape_ga_train_240604/ga"

# ga_config = TwoDThreeDGAConfig(database=ga_database,
#                                base_intan_path=base_intan_path)
ga_config = TrainingAlexNetMockGeneticAlgorithmConfig(database=ga_database,
                                                      base_intan_path=base_intan_path)

ga_config.ga_name = ga_name

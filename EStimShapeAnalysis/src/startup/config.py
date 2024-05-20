from src.pga.config.twod_threed_config import TwoDThreeDGAConfig
from src.pga.mock.alexnet_mock_ga import FullAutoAlexNetMockGeneticAlgorithmConfig, \
    TrainingAlexNetMockGeneticAlgorithmConfig

ga_name = "New3D"
ga_database = "allen_estimshape_ga_test_240508"
nafc_database = "allen_estimshape_test_240508"
isogabor_database = "allen_isogabor_test_240508"
allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
image_path = "/home/r2_allen/Documents/EStimShape/allen_estimshape_ga_test_240508/stimuli/ga/pngs"
java_output_dir = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/java_output"
rwa_output_dir = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/rwa"
base_intan_path = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/allen_estimshape_ga_test_240502/ga"

# ga_config = TwoDThreeDGAConfig(database=ga_database,
#                                base_intan_path=base_intan_path)
ga_config = TrainingAlexNetMockGeneticAlgorithmConfig(database=ga_database,
                                                      base_intan_path=base_intan_path)

ga_config.ga_name = ga_name

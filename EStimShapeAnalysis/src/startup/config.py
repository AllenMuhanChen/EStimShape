from src.pga.config.twod_threed_config import TwoDThreeDGAConfig
from src.pga.mock.alexnet_mock_ga import FullAutoAlexNetMockGeneticAlgorithmConfig, \
    TrainingAlexNetMockGeneticAlgorithmConfig

ga_name = "New3D"
ga_database = "allen_estimshape_ga_test_240604"
nafc_database = "allen_estimshape_test_240604"
isogabor_database = "allen_isogabor_test_240604"
allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
image_path = f"/home/r2_allen/Documents/EStimShape/{ga_database}/stimuli/ga/pngs"
java_output_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}/java_output"
rwa_output_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}/rwa"
eyecal_dir=f"/home/r2_allen/Documents/EStimShape/{ga_database}/eyecal"
base_intan_path = f"/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/{ga_database}/ga"

# ga_config = TwoDThreeDGAConfig(database=ga_database,
#                                base_intan_path=base_intan_path)
ga_config = TrainingAlexNetMockGeneticAlgorithmConfig(database=ga_database,
                                                      base_intan_path=base_intan_path)

ga_config.ga_name = ga_name

from src.pga.config.twod_threed_config import TwoDThreeDGAConfig

ga_name = "New3D"
ga_database = "allen_ga_test_250304_1"
nafc_database = "allen_estimshape_test_250304_1"
isogabor_database = "allen_isogabor_test_250304_1"
twodvsthreed_database = "allen_twodvsthreed_test_250304_1"

allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"

# Dirs for GA
image_path = f"/home/r2_allen/Documents/EStimShape/{ga_database}/stimuli/ga/pngs"
java_output_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}/java_output"
rwa_output_dir = f"/home/r2_allen/Documents/EStimShape/{ga_database}/rwa"
eyecal_dir=f"/home/r2_allen/Documents/EStimShape/{ga_database}/eyecal"

# Local path for Intan Files (.dat)
ga_intan_path = f"/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/{ga_database}"
isogabor_intan_path = f"/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/{isogabor_database}"
twodvsthreed_intan_path = f"/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/{twodvsthreed_database}"

# Storage of Parsed Spikes from MultiFile Parser
ga_parsed_spikes_path = f"/home/r2_allen/Documents/EStimShape/{ga_database}/parsed_spikes"
isogabor_parsed_spikes_path = f"/home/r2_allen/Documents/EStimShape/{isogabor_database}/parsed_spikes"
twodvsthreed_parsed_spikes_path = f"/home/r2_allen/Documents/EStimShape/{twodvsthreed_database}/parsed_spikes"

try:
    ga_config = TwoDThreeDGAConfig(database=ga_database,
                                   base_intan_path=ga_intan_path,
                                   java_output_dir=java_output_dir,
                                   allen_dist_dir=allen_dist)
    # ga_config = TrainingAlexNetMockGeneticAlgorithmConfig(database=ga_database,
    #                                                       base_intan_path=base_intan_path,
    #                                                       java_output_dir=java_output_dir,
    #                                                       allen_dist_dir=allen_dist)
    ga_config.ga_name = ga_name
except:
    print("Error in creating GA config")


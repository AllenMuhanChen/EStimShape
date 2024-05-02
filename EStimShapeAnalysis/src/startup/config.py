from pga.config.twod_threed_config import TwoDThreeDGAConfig
ga_name = "New3D"
ga_database = "allen_estimshape_ga_test_240502"
nafc_database = "allen_estimshape_test_240502"
isogabor_database = "allen_isogabor_test_240502"
allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
image_path = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/pngs"
java_output_dir = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/java_output"
rwa_output_dir = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/rwa"

ga_config = TwoDThreeDGAConfig(ga_database)
ga_config.ga_name = ga_name




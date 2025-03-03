from src.pga.config.twod_threed_config import TwoDThreeDGAConfig

ga_name = "New3D"
ga_database = "allen_ga_train_250213_0"
nafc_database = "allen_estimshape_train_250213_0"
isogabor_database = "allen_isogabor_train_250213_0"
twodvsthreed_database = "allen_twodvsthreed_train_250213_0"
allen_dist = "/home/r2_allen/git/EStimShape/xper-train/dist/allen"
image_path = f"/home/r2_allen/Documents/EStimShape/allen_ga_train_250213_0/stimuli/ga/pngs"
java_output_dir = f"/home/r2_allen/Documents/EStimShape/allen_ga_train_250213_0/java_output"
rwa_output_dir = f"/home/r2_allen/Documents/EStimShape/allen_ga_train_250213_0/rwa"
eyecal_dir=f"/home/r2_allen/Documents/EStimShape/allen_ga_train_250213_0/eyecal"
ga_intan_path = f"/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/allen_ga_train_250213_0"
isogabor_intan_path = f"/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/allen_isogabor_train_250213_0"
twodvsthreed_intan_path = f"/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/allen_twodvsthreed_train_250213_0"

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


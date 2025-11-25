from src.pga.config.simultaneous_2dvs3d_config import Simultaneous3Dvs2DConfig
ga_name = "New3D"
ga_database = "allen_ga_exp_251008_0"
nafc_database = "allen_estimshape_exp_251008_0"
isogabor_database = "allen_isogabor_exp_251008_0"
lightness_database = "allen_lightness_exp_251008_0"
shuffle_database = "allen_shuffle_exp_251008_0"

base_dir = "/home/connorlab/Documents/EStimShape"
allen_dist = "/home/connorlab/git/EStimShape/xper-train/dist/allen"

# Dirs for GA
image_path = f"{base_dir}/{ga_database}/stimuli/ga/pngs"
java_output_dir = f"{base_dir}/{ga_database}/java_output"
rwa_output_dir = f"{base_dir}/{ga_database}/rwa"
eyecal_dir = f"{base_dir}/{ga_database}/eyecal"

# Local path for Intan Files (.dat)
ga_intan_path = f"/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/{ga_database}"
isogabor_intan_path = f"/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/{isogabor_database}"
lightness_intan_path = f"/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/{lightness_database}"
shuffle_intan_path = f"/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/{shuffle_database}"

# Storage of Parsed Spikes from MultiFile Parser
ga_parsed_spikes_path = f"{base_dir}/{ga_database}/parsed_spikes"
isogabor_parsed_spikes_path = f"{base_dir}/{isogabor_database}/parsed_spikes"
lightness_parsed_spikes_path = f"{base_dir}/{lightness_database}/parsed_spikes"
shuffle_parsed_spikes_path = f"{base_dir}/{shuffle_database}/parsed_spikes"

# Storage of plots
ga_plot_path = f"{base_dir}/{ga_database}/plots"
isogabor_plot_path = f"{base_dir}/{isogabor_database}/plots"
lightness_plot_path = f"{base_dir}/{lightness_database}/plots"
shuffle_plot_path = f"{base_dir}/{shuffle_database}/plots"
pc_maps_path = f"{base_dir}/{ga_database}/pc_maps"
try:

    ga_config = Simultaneous3Dvs2DConfig(
                                   is_alexnet_mock=False,
                                   database=ga_database,
                                   base_intan_path=ga_intan_path,
                                   java_output_dir=java_output_dir,
                                   allen_dist_dir=allen_dist)
    ga_config.ga_name = ga_name
except:
    print("Error in creating GA config")
    # print exception:
    import traceback
    traceback.print_exc()


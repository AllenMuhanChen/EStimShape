
import argparse
import os
from datetime import datetime

from clat.intan.amplifiers import read_amplifier_data_with_mmap
from clat.intan.rhd import load_intan_rhd_format
import numpy as np


from probeinterface import generate_linear_probe
import spikeinterface as si
import spikeinterface.preprocessing as spre
import spikeinterface.sorters as ss




def get_recording_session_info(intan_file_dir):
    info_rhd_path = os.path.join(intan_file_dir, "info.rhd")
    data = load_intan_rhd_format.read_data(info_rhd_path)
    enabled_channels = data['amplifier_channels']
    sample_rate = data['frequency_parameters']['amplifier_sample_rate']
    return sample_rate, enabled_channels


def compute_device_channel_index(enabled_channels):
    probe_channel_order = np.array(
        [25, 6, 21, 10, 26, 5, 20, 11, 22, 9, 27, 4, 19, 12, 28, 3, 24, 7, 18, 13, 29, 2, 17, 14, 31, 0, 23, 8, 30, 1,
         16, 15])

    # Map native_order -> recording channel index (0..N-1) in the .dat
    native_to_recidx = {}
    for rec_idx, ch in enumerate(enabled_channels):
        native_to_recidx[ch["native_order"]] = rec_idx
    print(f"native_to_reidx {native_to_recidx}")
    # For each probe contact index, fill the corresponding recording channel index or -1
    device_channel_idx = []
    for contact_idx, native_order in enumerate(probe_channel_order):
        rec_idx = native_to_recidx.get(native_order, -1)
        device_channel_idx.append(rec_idx)
    print(f"Device channel idx: {device_channel_idx}")
    return device_channel_idx


if __name__ == '__main__':
    global_job_kwargs = dict(n_jobs=4, chunk_duration="1s")
    si.set_global_job_kwargs(**global_job_kwargs)

    # For running shell script (running a list of different sessions)
    # p = argparse.ArgumentParser()
    # p.add_argument("--date", required=True)   # e.g., 2023-10-10
    # p.add_argument("--round", type=int, required=True)
    # args = p.parse_args()
    #
    # date = args.date
    # round = args.round
    date = "2023-09-26"
    round = 1

    date_obj = datetime.strptime(date, "%Y-%m-%d")
    date_str = date_obj.strftime("%y%m%d")  # → "230926"

    # build paths safely
    round_folder = f"{date_str}_round{round}"
    base_dir = os.path.join(
        "/home/connorlab/Documents/IntanData/Cortana", date, round_folder
    )

    # Read recording
    intan_file_directory = base_dir
    sampling_frequency, channels = get_recording_session_info(intan_file_directory)
    folder_name = os.path.basename(os.path.normpath(intan_file_directory))
    print(f"sorting session: {folder_name}")
    recording = si.read_binary(os.path.join(intan_file_directory, "amplifier.dat"),
                               sampling_frequency=sampling_frequency, dtype=np.int16,
                               num_channels=len(channels), gain_to_uV=0.195, offset_to_uV=0.0)

    probe = generate_linear_probe(num_elec=32, ypitch=65,
                                  contact_shapes="circle", contact_shape_params={"radius": 20})
    device_channel_idx = compute_device_channel_index(channels)
    probe.set_device_channel_indices(device_channel_idx)
    recording = recording.set_probe(probe)

    # Pre-Processing
    recording_f = spre.bandpass_filter(recording, freq_min=300, freq_max=6000)
    recording_preprocessed = spre.common_reference(recording_f, reference="global", operator="median")

    # Sort
    sorting_KS4 = ss.run_sorter(sorter_name="kilosort4", recording=recording_preprocessed,
                                docker_image="spikeinterface/kilosort4-base:4.0.38_cuda-12.0.0",
                                folder=os.path.join(intan_file_directory, "kilosort4_output"),
                                remove_existing_folder=True, verbose=False)
    sorting_TDC = ss.run_sorter(sorter_name="tridesclous", recording=recording_preprocessed,
                                folder=os.path.join(intan_file_directory, "tridesclous_output"),
                                remove_existing_folder=True, verbose=False)
    sorting_MS5 = ss.run_sorter(sorter_name="mountainsort5", recording=recording_preprocessed,
                                folder=os.path.join(intan_file_directory, "mountainsort5_output"),
                                docker_image="spikeinterface/mountainsort5-base:latest",
                                remove_existing_folder=True, verbose=False)

    # Create Sorting Analyzer
    analyzer_KS4 = si.create_sorting_analyzer(sorting=sorting_KS4, recording=recording_preprocessed,
                                              format='binary_folder', overwrite=True,
                                              folder=os.path.join(intan_file_directory, 'analyzer_KS4_binary'))
    analyzer_TDC = si.create_sorting_analyzer(sorting=sorting_TDC, recording=recording_preprocessed,
                                              format='binary_folder', overwrite=True,
                                              folder=os.path.join(intan_file_directory, 'analyzer_TDC_binary'))
    analyzer_MS5 = si.create_sorting_analyzer(sorting=sorting_MS5, recording=recording_preprocessed,
                                              format='binary_folder', overwrite=True,
                                              folder=os.path.join(intan_file_directory, 'analyzer_MS5_binary'))

    # Compute Extensions
    extensions_to_compute = [
        "random_spikes",
        "waveforms",
        "templates",
        "correlograms"
    ]

    analyzer_KS4.compute(extensions_to_compute)
    analyzer_TDC.compute(extensions_to_compute)
    analyzer_MS5.compute(extensions_to_compute)


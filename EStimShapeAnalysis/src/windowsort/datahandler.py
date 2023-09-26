import os
import pickle
from typing import Dict

import numpy as np
from scipy.signal import butter, filtfilt

from intan.amplifiers import read_amplifier_data
from intan.channels import Channel
from intan.rhd import load_intan_rhd_format


class DataImporter:
    def __init__(self, intan_file_directory):
        self.intan_file_directory = intan_file_directory
        self.voltages_by_channel: dict[Channel, np.ndarray] = {}
        self.sample_rate = None  # You can initialize this from info.rhd if needed
        self.read_data()

    def read_data(self):
        # Assuming info.rhd and amplifier.dat are in the same directory
        info_rhd_path = os.path.join(self.intan_file_directory, "info.rhd")
        amplifier_dat_path = os.path.join(self.intan_file_directory, "amplifier.dat")

        # Extract information from info.rhd
        # Replace the following line with your actual method to read info.rhd
        data = load_intan_rhd_format.read_data(info_rhd_path)
        amplifier_channels = data['amplifier_channels']
        self.sample_rate = data['frequency_parameters']['amplifier_sample_rate']
        # Use your existing read_amplifier_data function
        self.voltages_by_channel = read_amplifier_data(amplifier_dat_path, amplifier_channels)
        # Preprocess the data after reading it
        self.preprocess_data()

    def preprocess_data(self):
        for channel, voltages in self.voltages_by_channel.items():
            self.voltages_by_channel[channel] = self.highpass_filter(voltages, cutoff=300)

    def butter_highpass(self, cutoff, fs, order=5):
        nyquist = 0.5 * fs
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype='high', analog=False)
        return b, a

    def highpass_filter(self, data, cutoff=300, order=5):
        b, a = self.butter_highpass(cutoff, self.sample_rate, order=order)
        y = filtfilt(b, a, data)
        return y


class DataExporter:
    def __init__(self, *, save_directory):
        self.thresholded_spike_indices_by_channel = {}  # Keyed by channel, each value is a list of spike times
        self.sorted_spikes_by_unit_by_channel = {}  # Keyed by channel, each value is a dict of unit name to spike times
        self.save_directory = save_directory

    def update_thresholded_spikes(self, channel, thresholded_spike_indices):
        self.thresholded_spike_indices_by_channel[channel] = thresholded_spike_indices

    def export_data(self):
        filename = os.path.join(self.save_directory, "thresholded_spikes.pkl")
        with open(filename, 'wb') as f:
            pickle.dump(self.thresholded_spike_indices_by_channel, f)
        # print(f"Saved {len(self.thresholded_spikes_by_channel.items())} thresholded spikes to {self.filename}")
        print(self.thresholded_spike_indices_by_channel)

    def save_sorted_spikes(self, spikes_by_unit: Dict[str, np.ndarray], channel):
        filename = os.path.join(self.save_directory, "sorted_spikes.pkl")

        # First, check if the file already exists.
        if os.path.exists(filename):
            # Load the existing data.
            with open(filename, 'rb') as f:
                existing_data = pickle.load(f)
        else:
            existing_data = {}

        # Update the specific channel's data in-memory.
        existing_data[channel] = spikes_by_unit

        # Now, save the updated data back to the file.
        with open(filename, 'wb') as f:
            pickle.dump(existing_data, f)

        print(existing_data)

    def save_sorting_config(self, channel, amp_time_windows, units, threshold):
        filename = os.path.join(self.save_directory, 'sorting_config.pkl')
        try:
            with open(filename, 'rb') as f:
                all_configs = pickle.load(f)
        except FileNotFoundError:
            all_configs = {}

        all_configs[channel] = {
            'amp_time_windows': [(window.sort_x, window.sort_ymin, window.sort_ymax) for window in amp_time_windows],
            'units': [(unit.logical_expression, unit.unit_name, unit.color) for unit in units],
            'threshold': threshold
        }

        with open(filename, 'wb') as f:
            pickle.dump(all_configs, f)

        print("Saved sorting configs to: ", filename)

    def load_sorting_config(self, channel: Channel):
        try:
            filename = os.path.join(self.save_directory,'sorting_config.pkl')
            with open(filename, 'rb') as f:
                all_configs = pickle.load(f)
            return all_configs.get(channel, None)
        except FileNotFoundError:
            print("Configuration file not found.")
            return None

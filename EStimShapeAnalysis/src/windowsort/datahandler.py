import os
import numpy as np

from intan.amplifiers import read_amplifier_data
from intan.channels import Channel
from intan.rhd import load_intan_rhd_format


class DataHandler:
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


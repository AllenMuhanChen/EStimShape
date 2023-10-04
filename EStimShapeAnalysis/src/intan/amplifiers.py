import numpy as np
import os

from intan.channels import Channel

import numpy as np
from intan.channels import Channel  # Assuming you have this import
import os


def read_amplifier_data_with_memmap(file_path, amplifier_channels):
    """
    Reads amplifier data from a binary file and maps it to memory.
    Creates a dictionary mapping each native_channel_name to its vector of spikes.

    Parameters:
    - file_path: str, path to the amplifier.dat file
    - amplifier_channels: list of dicts, amplifier channel information

    Returns:
    - channel_to_data: dict, mapping from native_channel_name to spike data in microvolts
    """
    # Extract the number of channels
    num_channels = len(amplifier_channels)

    # Get file size in bytes
    fileinfo = os.path.getsize(file_path)

    # Calculate the number of samples
    num_samples = fileinfo // (num_channels * 2)  # int16 = 2 bytes

    # Initialize an empty dictionary to store the mapping
    channel_to_data = {}

    # Create a memory-mapped array that maps the binary file to an array
    fp = np.memmap(file_path, dtype='int16', mode='r', shape=(num_samples, num_channels))

    # Convert the data to microvolts and populate the dictionary
    for i, channel_info in enumerate(amplifier_channels):
        print(f"Reading channel {i}...")
        native_channel_name = channel_info.get("native_channel_name", f"Channel_{i}")
        channel_data = fp[:, i] * 0.195  # Conversion to microvolts
        channel_to_data[Channel(native_channel_name)] = channel_data

    return channel_to_data


def read_amplifier_data(file_path, amplifier_channels):
    """
    Reads amplifier data from a binary file and converts it to microvolts.
    Creates a dictionary mapping each native_channel_name to its vector of spikes.

    Parameters:
    - file_path: str, path to the amplifier.dat file
    - amplifier_channels: list of dicts, amplifier channel information

    Returns:
    - channel_to_data: dict, mapping from native_channel_name to spike data in microvolts
    """
    # Extract the number of channels
    num_channels = len(amplifier_channels)

    # Get file size in bytes
    fileinfo = os.path.getsize(file_path)

    # Calculate the number of samples
    num_samples = fileinfo // (num_channels * 2)  # int16 = 2 bytes

    # Initialize an empty dictionary to store the mapping
    channel_to_data = {}

    # Open the file and read the data
    with open(file_path, 'rb') as fid:
        v = np.fromfile(fid, dtype=np.int16, count=num_channels * num_samples)

    # Reshape and transpose the array to get the proper dimensions
    v = v.reshape((num_samples, num_channels)).T

    # Convert to microvolts
    v = v * 0.195

    # Populate the dictionary
    for i, channel_info in enumerate(amplifier_channels):
        native_channel_name = channel_info.get("native_channel_name", f"Channel_{i}")
        channel_to_data[Channel(native_channel_name)] = v[i, :]

    return channel_to_data

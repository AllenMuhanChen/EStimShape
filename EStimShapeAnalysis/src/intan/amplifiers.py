import numpy as np
import os


def read_amplifier_data(file_path, amplifier_channels):
    """
    Reads amplifier data from a binary file and converts it to microvolts.

    Parameters:
    - file_path: str, path to the amplifier.dat file
    - amplifier_channels: list, amplifier channel information

    Returns:
    - v: numpy.ndarray, amplifier data in microvolts
    """
    num_channels = len(amplifier_channels)

    # Get file size in bytes
    fileinfo = os.path.getsize(file_path)

    # Calculate the number of samples
    num_samples = fileinfo // (num_channels * 2)  # int16 = 2 bytes

    # Open the file and read the data
    with open(file_path, 'rb') as fid:
        v = np.fromfile(fid, dtype=np.int16, count=num_channels * num_samples)

    # Reshape and transpose the array to get the proper dimensions
    v = v.reshape((num_samples, num_channels)).T

    # Convert to microvolts
    v = v * 0.195

    return v




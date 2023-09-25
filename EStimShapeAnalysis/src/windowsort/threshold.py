import numpy as np


def threshold_spikes_absolute(threshold_value, voltages):
    # Find spikes that cross the threshold
    above_threshold = voltages < threshold_value
    crossing_indices = np.where(np.diff(above_threshold))[0]

    # Calculate the first derivative of the voltages
    voltage_derivative = np.diff(voltages)

    # Filter out indices where the derivative is positive or zero
    # This ensures that we only count spikes where the voltage is decreasing
    filtered_indices = [idx for idx in crossing_indices if voltage_derivative[idx] < 0]

    return np.array(filtered_indices)

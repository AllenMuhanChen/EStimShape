import os

import numpy as np


def epoch_using_marker_channels(digitalin_path, false_negative_correction_duration=40, false_positive_correction_duration=2) -> list[tuple[int, int]]:
    """
    :param digitalin_path: path to digitalin.dat file
    :param false_negative_correction_duration: the number of samples to check before or after a state switch to identify false negatives or positives
    :return: list of tuples of start and stop indices for each epoch
    """
    digitalin = read_digitalin_file(digitalin_path)
    return get_epochs_start_and_stop_indices(digitalin[0], digitalin[1], false_negative_correction_duration, false_positive_correction_duration)


def get_epochs_start_and_stop_indices(marker1_data, marker2_data, false_negative_correction_duration=2, false_positive_correction_duration=2) -> list[
    tuple[int, int]]:
    epochs = []
    start_time = None
    current_marker = determine_marker_with_first_pulse(marker1_data, marker2_data)

    for i in range(max(len(marker1_data), len(marker2_data))):

        if current_marker == 1:
            # Starting an epoch for marker 1
            if marker1_data[i] and start_time is None and not false_positive(i, marker1_data,
                                                                             false_positive_correction_duration):
                start_time = i
            # Ending an epoch for marker 1
            if not false_negative(i, false_negative_correction_duration, marker1_data):
                if is_end_of_epoch(i, marker1_data) and epoch_ongoing(start_time):
                    epochs.append((start_time, i))
                    start_time = None
                    current_marker = 2
            # Can't end epoch for marker 1 because silence period afterwards is too short
            else:
                print("Detected false negative for marker 1 at time {}".format(i + 1))

        else:
            if marker2_data[i] and start_time is None and not false_positive(i, marker2_data,
                                                                             false_positive_correction_duration):
                start_time = i
            if not false_negative(i, false_negative_correction_duration, marker2_data):
                if is_end_of_epoch(i, marker2_data) and epoch_ongoing(start_time):
                    epochs.append((start_time, i))
                    start_time = None
                    current_marker = 1
                # Can't end epoch for marker 1 because it's too short
            else:
                print("Detected false negative for marker 2 at time {}".format(i + 1))

    return epochs


def epoch_ongoing(start_time) -> bool:
    return start_time is not None


def is_end_of_epoch(i, marker_data) -> bool:
    try:
        return not marker_data[i + 1]
    except IndexError:
        return True


def false_positive(i, marker_data, min_duration) -> bool:
    # Check if any of the values ahead of time are False
    for j in range(i, i + min_duration):
        # If any of the values is False, that means this is a false positive
        try:
            if not marker_data[j]:
                return True
        except IndexError:
            return False


def false_negative(i, min_duration, marker_data) -> bool:
    # Check min_duration ahead of time
    for j in range(i + 1, i + min_duration + 1):
        # If any of the values is True, that means the epoch is not actually over
        try:
            if marker_data[j]:
                return True
        except IndexError:
            return False


def determine_marker_with_first_pulse(marker1_data, marker2_data) -> int:
    for i in range(len(marker1_data)):
        if marker1_data[i] and not marker2_data[i]:
            return 1
        elif marker2_data[i] and not marker1_data[i]:
            return 2
    return None


def read_digitalin_file(full_file_name) -> list[list[bool], list[bool]]:
    fid = open(full_file_name, 'rb')
    filesize = os.path.getsize(full_file_name)

    num_samples = filesize // 2  # uint16 = 2 bytes

    digital_word = np.fromfile(fid, dtype=np.uint16, count=num_samples)
    fid.close()

    # Get the digital inputs for channel 0 and 1
    digital_input_ch0 = (digital_word & (2 ** 0)) > 0
    digital_input_ch1 = (digital_word & (2 ** 1)) > 0

    return [digital_input_ch0, digital_input_ch1]


def isolate_digital_input(digital_word, ch):
    digital_input_ch = (digital_word & (2 ** ch)) > 0
    return digital_input_ch

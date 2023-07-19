def get_epochs_start_and_stop_indices(marker1_data, marker2_data, false_data_correction_duration=2) -> list[
    tuple[int, int]]:
    epochs = []
    start_time = None
    current_marker = determine_first_pulse(marker1_data, marker2_data)

    for i in range(max(len(marker1_data), len(marker2_data))):

        if current_marker == 1:
            # Starting an epoch for marker 1
            if marker1_data[i] and start_time is None and not false_positive(i, marker1_data,
                                                                             false_data_correction_duration):
                start_time = i
            # Ending an epoch for marker 1
            elif is_end_of_epoch(i, marker1_data) and epoch_ongoing(start_time) and not false_negative(i,
                                                                                                       false_data_correction_duration,
                                                                                                       marker1_data):
                epochs.append((start_time, i))
                start_time = None
                current_marker = 2
            # Can't end epoch for marker 1 because it's too short
            elif is_end_of_epoch(i, marker1_data) and epoch_ongoing(start_time) and false_negative(i,
                                                                                                   false_data_correction_duration,
                                                                                                   marker2_data):
                print("Detected false negative for marker 1 at time {}".format(i + 1))

        else:
            if marker2_data[i] and start_time is None and not false_positive(i, marker2_data,
                                                                             false_data_correction_duration):
                start_time = i
            elif is_end_of_epoch(i, marker2_data) and epoch_ongoing(start_time) and not false_negative(i,
                                                                                                       false_data_correction_duration,
                                                                                                       marker2_data):
                epochs.append((start_time, i))
                start_time = None
                current_marker = 1
                # Can't end epoch for marker 1 because it's too short
            elif is_end_of_epoch(i, marker2_data) and epoch_ongoing(start_time) and false_negative(i,
                                                                                                   false_data_correction_duration,
                                                                                                   marker2_data):
                print("Detected false negative for marker 2 at time {}".format(i + 1))

    return epochs


def epoch_ongoing(start_time):
    return start_time is not None


def is_end_of_epoch(i, marker_data):
    try:
        return not marker_data[i + 1]
    except IndexError:
        return True


def false_positive(i, marker_data, min_duration):
    # Check if any of the values ahead of time are False
    for j in range(i, i + min_duration):
        # If any of the values is False, that means this is a false positive
        try:
            if not marker_data[j]:
                return True
        except IndexError:
            return False


def false_negative(i, min_duration, marker_data):
    # Check min_duration ahead of time
    for j in range(i + 1, i + min_duration + 1):
        # If any of the values is True, that means the epoch is not actually over
        try:
            if marker_data[j]:
                return True
        except IndexError:
            return False


def determine_first_pulse(marker1_data, marker2_data):
    for i in range(len(marker1_data)):
        if marker1_data[i] and not marker2_data[i]:
            return 1
        elif marker2_data[i] and not marker1_data[i]:
            return 2
    return None

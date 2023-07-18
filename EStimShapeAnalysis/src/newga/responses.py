import os

from intan.read_intan_spike_file import read_intan_spike_file, read_digitalin_file


def fetch_spike_tstamps_from_file(spike_file_path):
    spike_matrix, sample_rate = read_intan_spike_file(spike_file_path)
    spike_tstamps_for_channels = spike_matrix_to_spike_tstamps_for_channels(spike_matrix)
    return spike_tstamps_for_channels


def filter_spikes_with_stim_tstamps(spike_tstamps_for_channels, tstamps_for_stim_ids, stim_id):
    passed_filter = []
    tstamps = tstamps_for_stim_ids[stim_id]
    for channel in spike_tstamps_for_channels:
        for spike_tstamp in channel:
            if spike_tstamp >= tstamps[0] or spike_tstamp <= tstamps[1]:
                passed_filter.append(spike_tstamp)
    return passed_filter


class ResponseParser:
    def __init__(self, base_intan_path: str):
        self.intan_spike_path = base_intan_path

    def parse_avg_spike_count_for_stim(self, stim_id):
        # Find the taks_ids for a stim_id

        # Parse all the spike counts
        # Add each to response_vector

        # average the spike counts
        # Assign as response
        pass

    def parse_spike_count_for_task(self, task_id):
        spike_tstamps_for_channels, sample_rate = fetch_spike_tstamps_from_file(self.path_to_spike(task_id))
        digital_in = read_digitalin_file(self.path_to_digital_in(task_id))
        stim_tstamps_from_markers = get_epochs(digital_in[0], digital_in[1])
        stim_id_for_tstamps = map_stim_id_to_tstamps(self.path_to_notes(task_id), stim_tstamps_from_markers)
        spikes_for_channels = filter_spikes_with_stim_tstamps(spike_tstamps_for_channels, stim_id_for_tstamps, task_id)
        return len(spikes_for_channels)

    def path_to_spike(self, stim_id: int) -> str:
        pass

    def path_to_digital_in(self, stim_id: int) -> str:
        pass

    def path_to_notes(self, stim_id: int) -> str:
        pass


def map_stim_id_to_tstamps(input_data: str, time_indices: list) -> dict:
    # Check if the input is a file path
    if os.path.isfile(input_data):
        with open(input_data, 'r') as file:
            data = file.read()
    else:
        data = input_data

    # Convert the raw text data into a list of tuples (tstamp, stim_id)
    tstamp_and_stim_id_from_livenotes = []
    for line in data.strip().split('\n\n'):
        parts = line.split(',')
        tstamp = int(parts[0].strip())
        stim_id = int(parts[2].strip())
        tstamp_and_stim_id_from_livenotes.append((tstamp, stim_id))

    # Sort the tstamp_and_stim_id_from_livenotes by tstamp
    tstamp_and_stim_id_from_livenotes.sort()

    # Initialize the dictionary to store the result
    result = {}

    # For each tuple in time_indices, find the record with the closest tstamp
    for start, end in time_indices:
        # Find the record with the tstamp closest to start
        closest_tstamp = None
        closest_stim_id = None
        for tstamp, stim_id in tstamp_and_stim_id_from_livenotes:
            if stim_id not in result and (closest_tstamp is None or abs(tstamp - start) < abs(closest_tstamp - start)):
                closest_tstamp = tstamp
                closest_stim_id = stim_id

        # If no match is found, raise an error
        if closest_stim_id is None:
            raise ValueError(f"No match found for start time {start}")

        # Otherwise, add it to the result
        result[closest_stim_id] = start

    return result


def get_epochs(marker1_data, marker2_data, false_data_correction_duration=2):
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
        # If any of the values is False, that means the epoch should not actually start
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


def spike_matrix_to_spike_tstamps_for_channels(spike_matrix):
    """
    Convert spike data into a dictionary of channel names and responses.
    """
    spike_dict = {}
    for row in spike_matrix:
        channel_name = row[0]
        responses = row[2]
        spike_dict[channel_name] = responses
    return spike_dict


def count_spikes_for_channels(spike_tstamps_for_channels):
    spike_counts_for_channels = {}
    for channel_name, spike_tstamps in spike_tstamps_for_channels.items():
        spike_counts_for_channels[channel_name] = len(spike_tstamps)
    return spike_counts_for_channels

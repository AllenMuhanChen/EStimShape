from intan.read_intan_spike_file import read_intan_spike_file


def fetch_spike_tstamps_from_file(spike_file_path):
    spike_matrix = read_intan_spike_file(spike_file_path)
    spike_tstamps_for_channels = spike_matrix_to_spike_tstamps_for_channels(spike_matrix)
    return spike_tstamps_for_channels


class ResponseParser:
    def __init__(self, intan_spike_path):
        self.intan_spike_path = intan_spike_path

    def parse_spike_count(self, stim_id):
        spike_file_path = self.stim_id_to_path(stim_id)
        spike_tstamps_for_channels, sample_rate = fetch_spike_tstamps_from_file(spike_file_path)
        digital_in = read_digitalin_file(self.digitalin_file_path(stim_id))
        stim_tstamps = get_epochs(spike_file_path)
        return filter_spikes_with_stim_tstamps(spike_tstamps_for_channels, stim_tstamps)

    def path_to_stim_id(self, stim_id):
        pass


def get_epochs(marker1_data, marker2_data, false_data_correction_duration=2):
    epochs = []
    start_time = None
    current_marker = determine_first_pulse(marker1_data, marker2_data)

    for i in range(max(len(marker1_data), len(marker2_data))):

        if current_marker == 1:
            # Starting an epoch for marker 1
            if marker1_data[i] and start_time is None and not false_positive(i, marker1_data, false_data_correction_duration):
                start_time = i
            # Ending an epoch for marker 1
            elif is_end_of_epoch(i, marker1_data) and epoch_ongoing(start_time) and not false_negative(i, false_data_correction_duration,
                                                                                                       marker1_data):
                epochs.append((start_time, i))
                start_time = None
                current_marker = 2
            # Can't end epoch for marker 1 because it's too short
            elif is_end_of_epoch(i, marker1_data) and epoch_ongoing(start_time) and false_negative(i, false_data_correction_duration,
                                                                                                   marker2_data):
                print("Detected false negative for marker 1 at time {}".format(i+1))

        else:
            if marker2_data[i] and start_time is None and not false_positive(i, marker2_data, false_data_correction_duration):
                start_time = i
            elif is_end_of_epoch(i, marker2_data) and epoch_ongoing(start_time) and not false_negative(i, false_data_correction_duration, marker2_data):
                epochs.append((start_time, i))
                start_time = None
                current_marker = 1
                # Can't end epoch for marker 1 because it's too short
            elif is_end_of_epoch(i, marker2_data) and epoch_ongoing(start_time) and false_negative(i, false_data_correction_duration,
                                                                                                   marker2_data):
                print("Detected false negative for marker 2 at time {}".format(i+1))

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

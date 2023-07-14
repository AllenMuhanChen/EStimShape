from intan.read_intan_spike_file import read_intan_spike_file


def fetch_spike_tstamps_from_file(spike_file_path):
    spike_matrix = read_intan_spike_file(spike_file_path)
    spike_tstamps_for_channels = spike_matrix_to_spike_tstamps_for_channels(spike_matrix)
    return spike_tstamps_for_channels


class ResponseRetriever:
    def __init__(self, intan_spike_path):
        self.intan_spike_path = intan_spike_path

    def retrieve_responses(self, stim_id):
        spike_file_path = stim_id_to_path(stim_id)
        spike_counts_for_channels = fetch_spike_tstamps_from_file(spike_file_path)
        stim_tstamps = fetch_stim_tstamps_from_file(spike_file_path)

        return spike_counts_for_channels

    def stim_id_to_path(self, stim_id):
        pass


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

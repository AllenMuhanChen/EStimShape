import os


def parse_data_type(data_type, session_id, filename, raw_save_dir):
    if data_type == 'raw':
        response_table = 'RawSpikeResponses'
        save_path = f"{raw_save_dir}/{filename}"
        spike_tstamps_col = 'Spikes by channel'
        spike_rates_col = 'Spike Rate by channel'
    elif data_type == 'sorted':
        response_table = 'WindowSortedResponses'
        spike_tstamps_col = 'Spikes by unit'
        spike_rates_col = 'Spike Rate by unit'
        save_path = f"/home/r2_allen/Documents/EStimShape/allen_sort_{session_id}/plots/{filename}"


    else:
        raise ValueError(f"Unknown data type: {data_type}")
    return response_table, save_path, spike_tstamps_col, spike_rates_col

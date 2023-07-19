import os


def map_stim_id_to_epochs_with_livenotes(livenotes_data: str, marker_channel_time_indices: list[tuple]) -> dict[int, tuple]:
    """
    Params:
    livenotes_data: live_notes file in the form a path or the file string itself
    marker_channel_time_indices: list of tuples (start, end) where start and end are the start and end time indices of the stimulus
    based on marker_channel data

    Returns:
    mapping of the stim_ids in the livenotes with the real marker-channel based tuples (start, end)
    based on closest matching between timestamp in livenotes and start time in marker-channel data

    """
    # Check if the input is a file path
    if os.path.isfile(livenotes_data):
        with open(livenotes_data, 'r') as file:
            data = file.read()
    else:
        data = livenotes_data

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

    # For each tuple in time_indices, find the one with the closest tstamp
    for start, end in marker_channel_time_indices:
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

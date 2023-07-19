import os


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

    # For each tuple in time_indices, find the one with the closest tstamp
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

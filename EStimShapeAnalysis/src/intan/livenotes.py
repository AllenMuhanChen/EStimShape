import os
from typing import Tuple, List, Dict


def map_task_id_to_epochs_with_livenotes(livenotes_data: str,
                                         marker_channel_time_indices: List[Tuple[int, int]]) -> Dict[
    int, Tuple[int, int]]:
    """
    Map unique task IDs to epochs with a following 'Trial Complete' event,
    such that if there are repetitions of a task id in the livenotes, only the complete instance will
    be returned.
    """
    data = read_livenotes(livenotes_data)
    events = parse_livenotes_to_events(data)
    stim_ids = filter_for_stim_ids(events)
    stim_ids.sort()

    result = {}

    # Loop through each stim_id and find the closest marker channel to it
    # that has a following 'Trial Complete' event
    for tstamp, stim_id in stim_ids:
        closest_start = None
        closest_end = None
        following_event = None

        idx = events.index((tstamp, str(stim_id)))  # Find the index of this stim_id in the original events list
        if idx < len(events) - 1:
            following_event = events[idx + 1][1]  # Get the following event

        # Only proceed if the following event is 'Trial Complete'
        if following_event == 'Trial Complete':
            for start, end in marker_channel_time_indices:
                if closest_start is None or abs(tstamp - start) < abs(tstamp - closest_start):
                    closest_start = start
                    closest_end = end

            if closest_start is not None and result.get(stim_id) is None:
                result[stim_id] = (closest_start, closest_end)

    return result


def map_unique_task_id_to_epochs_with_livenotes(livenotes_data: str,
                                                marker_channel_time_indices: List[tuple]) -> dict[
    int, Tuple[int, int]]:
    """
    This functions requires task_ids to be unique in the livenotes file. If there are multiple task_ids in the livenotes, it will output the
    all instances of the task_id: (start, end) in the marker_channel_time_indices

    Params:
    livenotes_data: live_notes file in the form a path or the file string itself
    marker_channel_time_indices: list of tuples (start, end) where start and end are the start and end time indices of the stimulus
    based on marker_channel data

    Returns:
    mapping of the stim_ids in the livenotes with the real marker-channel based tuples (start, end)
    based on closest matching between timestamp in livenotes and start time in marker-channel data

    """
    data = read_livenotes(livenotes_data)

    tstamp_and_events_from_livenotes = parse_livenotes_to_events(data)
    tstamp_and_stim_id_from_livenotes = filter_for_stim_ids(tstamp_and_events_from_livenotes)

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
            print(f"No match found for start time {start} found in marker channels")

        # Otherwise, add it to the result
        result[closest_stim_id] = (start, end)

    return result


def filter_for_stim_ids(tstamp_and_events_from_livenotes: List[Tuple[float, str]]) -> List[Tuple[float, int]]:
    filtered = []
    for tstamp, event in tstamp_and_events_from_livenotes:
        try:
            stim_id = int(event)
            filtered.append((tstamp, stim_id))
        except ValueError:
            continue
    return filtered


def parse_livenotes_to_events(data: str) -> List[Tuple[int, str]]:
    # Convert the raw text data into a list of tuples (tstamp, stim_id)
    tstamp_and_events_from_livenotes = []
    for line in data.strip().split('\n\n'):
        try:
            parts = line.split(',')
            tstamp = int(parts[0].strip())
            event = parts[2].strip()
            tstamp_and_events_from_livenotes.append((tstamp, event))
        except IndexError:
            print(f"Error parsing line {line}")
            continue

    return tstamp_and_events_from_livenotes


def read_livenotes(livenotes_data: str) -> str:
    # Check if the input is a file path
    if os.path.isfile(livenotes_data):
        with open(livenotes_data, 'r') as file:
            data = file.read()
    else:
        data = livenotes_data
    return data

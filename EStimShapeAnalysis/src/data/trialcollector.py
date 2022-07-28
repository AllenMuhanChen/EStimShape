import pandas as pd
import numpy as np
from src.database import reader
from src.when import timeutil

def collect_trials():
    beh_msg = reader.get_beh_msg()
    trial_starts = beh_msg[beh_msg['type'] == "TrialStart"]['tstamp'].values
    trial_stops = beh_msg[beh_msg['type'] == "TrialStop"]['tstamp'].values
    trial_starts, trial_stops = __ensure_ends_are_aligned(trial_starts, trial_stops)
    trial_starts, trial_stops = __ensure_balanced_trial_nums(trial_starts, trial_stops)
    trial_starts, trial_stops = __remove_misaligned_trials(trial_starts, trial_stops)
    return [timeutil.When(trial_starts[i], trial_stops[i]) for i in range(len(trial_starts))]


def __ensure_ends_are_aligned(trial_starts, trial_stops):
    while trial_stops[0] < trial_starts[0]:
        trial_stops = trial_stops[1:]
    while trial_starts[-1] > trial_stops[-1]:
        trial_starts = trial_starts[:-1]
    return trial_starts, trial_stops


def __ensure_balanced_trial_nums(trial_starts, trial_stops):
    while trial_starts.size != trial_stops.size:
        if trial_starts.size > trial_stops.size:
            diff_length = trial_starts.size - trial_stops.size
            first_bad_trial = get_first_bad_trial(trial_starts[:-diff_length], trial_stops)
            trial_starts = np.delete(trial_starts, first_bad_trial)
        else:
            diff_length = trial_stops.size - trial_starts.size
            first_bad_trial = get_first_bad_trial(trial_starts, trial_stops[:-diff_length])
            trial_stops = np.delete(trial_stops, first_bad_trial)
    return trial_starts, trial_stops

def __remove_misaligned_trials(trial_starts, trial_stops):
    while (not __trials_aligned(trial_starts, trial_stops)):
        first_bad_trial = get_first_bad_trial(trial_starts, trial_stops)
        trial_starts = np.delete(trial_starts, first_bad_trial)
        trial_stops = np.delete(trial_stops, first_bad_trial)
    return trial_starts, trial_stops


def get_first_bad_trial(trial_starts, trial_stops):
    bad_trials = np.array(trial_starts > trial_stops)
    first_bad_trial = [i for i, x in enumerate(bad_trials) if x][0]
    return first_bad_trial


def __trials_aligned(trial_starts, trial_stops):
    actual_correctly_aligned = sum([True for i in range(len(trial_starts)) if (trial_starts[i] < trial_stops[i])])
    return actual_correctly_aligned == len(trial_starts)




whens = collect_trials()
print(len(whens))

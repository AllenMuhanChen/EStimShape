import numpy as np
import pandas as pd
from src.data import reader, timeutil, table_util

beh_msg = reader.get_beh_msg()
stim_spec = reader.get_stim_sec()
def collect_choice_trials():
    all_trial_whens = collect_trials()
    choice_trial_whens = []
    for when in all_trial_whens:
        if table_util.contains_success(beh_msg, when):
            choice_trial_whens.append(when)
    return choice_trial_whens



def collect_trials():
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
            first_bad_trial = __get_first_bad_trial(trial_starts[:-diff_length], trial_stops)
            trial_starts = np.delete(trial_starts, first_bad_trial)
        else:
            diff_length = trial_stops.size - trial_starts.size
            first_bad_trial = __get_first_bad_trial(trial_starts, trial_stops[:-diff_length])
            trial_stops = np.delete(trial_stops, first_bad_trial)
    return trial_starts, trial_stops


def __remove_misaligned_trials(trial_starts, trial_stops):
    while not __trials_aligned(trial_starts, trial_stops):
        first_bad_trial = __get_first_bad_trial(trial_starts, trial_stops)
        trial_starts = np.delete(trial_starts, first_bad_trial)
        trial_stops = np.delete(trial_stops, first_bad_trial)
    return trial_starts, trial_stops


def __get_first_bad_trial(trial_starts, trial_stops):
    bad_trials = np.array(trial_starts > trial_stops)
    first_bad_trial = [i for i, x in enumerate(bad_trials) if x][0]
    return first_bad_trial


def __trials_aligned(trial_starts, trial_stops):
    actual_correctly_aligned = sum([True for i in range(len(trial_starts)) if (trial_starts[i] < trial_stops[i])])
    return actual_correctly_aligned == len(trial_starts)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    pass

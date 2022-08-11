import numpy as np
import pandas as pd
<<<<<<< HEAD
from src.data import connection, timeutil, table_util


class TrialCollector:
    def __init__(self, conn: connection.Connection):
        self.beh_msg = conn.beh_msg
        self.stim_spec = conn.stim_spec
        self.stim_obj_data = conn.stim_obj_data
=======
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
>>>>>>> 56d5c669cd40f00458aeb689625709c0bf48ea12

    def collect_choice_trials(self):
        all_trial_whens = self.collect_trials()
        choice_trial_whens = []
        for when in all_trial_whens:
            if table_util.contains_success(self.beh_msg, when):
                choice_trial_whens.append(when)
        return choice_trial_whens

    def collect_trials(self):
        trial_starts = self.beh_msg[self.beh_msg['type'] == "TrialStart"]['tstamp'].values
        print(len(self.beh_msg.index))
        print(len(trial_starts))
        trial_stops = self.beh_msg[self.beh_msg['type'] == "TrialStop"]['tstamp'].values
        trial_starts, trial_stops = self.__ensure_ends_are_aligned(trial_starts, trial_stops)
        trial_starts, trial_stops = self.__ensure_balanced_trial_nums(trial_starts, trial_stops)
        trial_starts, trial_stops = self.__remove_misaligned_trials(trial_starts, trial_stops)
        return [timeutil.When(trial_starts[i], trial_stops[i]) for i in range(len(trial_starts))]

    def __ensure_ends_are_aligned(self, trial_starts, trial_stops):
        while trial_stops[0] < trial_starts[0]:
            trial_stops = trial_stops[1:]
        while trial_starts[-1] > trial_stops[-1]:
            trial_starts = trial_starts[:-1]
        return trial_starts, trial_stops

<<<<<<< HEAD
    def __ensure_balanced_trial_nums(self, trial_starts, trial_stops):
        while trial_starts.size != trial_stops.size:
            if trial_starts.size > trial_stops.size:
                diff_length = trial_starts.size - trial_stops.size
                try:
                    first_bad_trial = self.__get_first_bad_trial(trial_starts[:-diff_length], trial_stops)
                except:
                    first_bad_trial = self.__get_first_bad_trial(trial_starts[diff_length:], trial_stops)
                trial_starts = np.delete(trial_starts, first_bad_trial)
            else:
                diff_length = trial_stops.size - trial_starts.size
                try:
                    first_bad_trial = self.__get_first_bad_trial(trial_starts, trial_stops[:-diff_length])
                except:
                    first_bad_trial = self.__get_first_bad_trial(trial_starts, trial_stops[diff_length:])
                trial_stops = np.delete(trial_stops, first_bad_trial)
        return trial_starts, trial_stops

    def __remove_misaligned_trials(self, trial_starts, trial_stops):
        while not self.__trials_aligned(trial_starts, trial_stops):
            first_bad_trial = self.__get_first_bad_trial(trial_starts, trial_stops)
            trial_starts = np.delete(trial_starts, first_bad_trial)
            trial_stops = np.delete(trial_stops, first_bad_trial)
        return trial_starts, trial_stops
=======
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
>>>>>>> 56d5c669cd40f00458aeb689625709c0bf48ea12

    def __get_first_bad_trial(self, trial_starts, trial_stops):
        bad_trials = np.array(trial_starts > trial_stops)
        first_bad_trial = [i for i, x in enumerate(bad_trials) if x][0]
        return first_bad_trial

<<<<<<< HEAD
    def __trials_aligned(self, trial_starts, trial_stops):
        actual_correctly_aligned = sum([True for i in range(len(trial_starts)) if (trial_starts[i] < trial_stops[i])])
        return actual_correctly_aligned == len(trial_starts)


=======
>>>>>>> 56d5c669cd40f00458aeb689625709c0bf48ea12
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    pass

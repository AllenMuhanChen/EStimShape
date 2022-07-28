# This is a sample Python scri
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import pandas as pd
import numpy as np
from src.data import trial_field as tf, timeutil, table_util, reader, trialcollector


class IsCorrectField(tf.Field):
    def __init__(self, beh_msg: pd.DataFrame):
        self.beh_msg = beh_msg
        self.name = "IsCorrect"

    def getValue(self, when: timeutil.When):
        time_cond = table_util.get_within_tstamps(self.beh_msg, when)
        correct = self.__get_num_corrects(time_cond)
        incorrect = self.__get_num_incorrects(time_cond)
        if correct == 1 and incorrect == 0:
            self.value = True
        elif incorrect == 1 and correct == 0:
            self.value = False
        elif correct > 1 or incorrect > 1:
            raise ValueError("There's more than one choice in this trial!")
        else:
            print(correct)
            print(incorrect)
            raise ValueError("There's no choice in this trial!")


    def __get_num_incorrects(self, time_cond):
        incorrect_trials = self.beh_msg['type'] == "ChoiceSelectionIncorect"
        incorrect = sum(np.logical_and(incorrect_trials, time_cond))
        return incorrect

    def __get_num_corrects(self, time_cond):
        correct_trials = self.beh_msg['type'] == "ChoiceSelectionCorrect"
        correct = sum(np.logical_and(correct_trials, time_cond))
        return correct


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    beh_msg = trialcollector.beh_msg
    trial_whens = trialcollector.collect_choice_trials()
    trialList = []
    for when in trial_whens:
        trialList.append(tf.Trial(when))

    fieldList = tf.FieldList()
    fieldList.append(IsCorrectField(beh_msg))

    for t in trialList:
        t.set_fields(fieldList)

    data = []

    for t in trialList:
        data = t.append_to_data(data)

    df = pd.DataFrame(data)
    print(sum(df["IsCorrect"])/len(df.index))
# See PyCharm help at https://www.jetbrains.com/help/pycharm/

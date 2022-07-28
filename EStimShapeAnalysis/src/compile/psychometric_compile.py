# This is a sample Python scri
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import pandas as pd
import numpy as np
from src.data import trial_field as tf
from src.data import timeutil
from src.data import table_util

class TrialTypeField(tf.Field):
    def __init__(self, beh_msg: pd.DataFrame):
        self.beh_msg = beh_msg
        self.name = "TrialType"

    def getValue(self, when: timeutil.When):
        time_cond = table_util.within_tstamps(self.beh_msg, when)
        correct = self.__get_num_corrects(time_cond)
        incorrect = self.__get_num_incorrects(time_cond)
        if correct == 1 and incorrect == 0:
            return True
        elif incorrect == 1 and correct == 1:
            return False
        elif correct > 1 or incorrect > 1:
            raise ValueError("There's more than one choice in this trial!")
        else:
            raise ValueError("There's no choice in this trial!")

    def __get_num_incorrects(self, time_cond):
        incorrect_cond = self.beh_msg['type'] == "ChoiceSelectionIncorrect"
        incorrect = sum(incorrect_cond & time_cond)
        return incorrect

    def __get_num_corrects(self, time_cond):
        correct_cond = self.beh_msg['type'] == "ChoiceSelectionCorrect"
        correct = sum(correct_cond & time_cond)
        return correct


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    reader.honk()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

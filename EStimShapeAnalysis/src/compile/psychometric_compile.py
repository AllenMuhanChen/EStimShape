# This is a sample Python scri
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
<<<<<<< HEAD
import datetime

import pandas as pd
import numpy as np
import xmltodict
from src.data import trial_field as tf, timeutil, table_util, connection, trialcollector

class StimSpecDataField(tf.Field):
    def __init__(self, beh_msg: pd.DataFrame, stim_spec: pd.DataFrame):
        self.beh_msg = beh_msg
        self.stim_spec = stim_spec

    def retrieve_spec_data(self, when):
        stim_spec_data_xml = table_util.get_stim_spec_data(self.beh_msg, self.stim_spec, when)
        stim_spec_data_dict = xmltodict.parse(stim_spec_data_xml)
        return stim_spec_data_dict

class TrialTypeField(StimSpecDataField):
    def __init__(self, beh_msg: pd.DataFrame, stim_spec: pd.DataFrame):
        self.name = "TrialType"
        super().__init__(beh_msg, stim_spec)

    def retrieveValue(self, when: timeutil.When):
        stim_spec_data_xml = self.retrieve_spec_data(when)
        msg_type = self._parse_type_from_stim_spec_data(stim_spec_data_xml)
        if ("RandNoisyTrialParameters" in msg_type):
            self.value = "Rand"
        elif ("Psychometric" in msg_type):
            self.value = "Psychometric"
        else:
            self.value = "Unknown"

    def _parse_type_from_stim_spec_data(self, stim_spec_data):
        try:
            return list(stim_spec_data.keys())[0]
        except:
            print(stim_spec_data)
            return "Unknown"

=======

import pandas as pd
import numpy as np
from src.data import trial_field as tf, timeutil, table_util, reader, trialcollector

class TrialTypeField(tf.Field):
    def __init__(self, beh_msg:pd.DataFrame, stim_spec:pd.DataFrame):
        self.name = "TrialType"
        self.beh_msg = beh_msg

    def getValue(self, when):
        pass
>>>>>>> 56d5c669cd40f00458aeb689625709c0bf48ea12

class IsCorrectField(tf.Field):
    def __init__(self, beh_msg: pd.DataFrame):
        self.beh_msg = beh_msg
        self.name = "IsCorrect"

<<<<<<< HEAD
    def retrieveValue(self, when: timeutil.When):
        time_cond = table_util.get_during_trial(self.beh_msg, when)
=======
    def getValue(self, when: timeutil.When):
        time_cond = table_util.get_within_tstamps(self.beh_msg, when)
>>>>>>> 56d5c669cd40f00458aeb689625709c0bf48ea12
        correct = self.__get_num_corrects(time_cond)
        incorrect = self.__get_num_incorrects(time_cond)
        if correct == 1 and incorrect == 0:
            self.value = True
        elif incorrect == 1 and correct == 0:
            self.value = False
        elif correct > 1 or incorrect > 1:
            raise ValueError("There's more than one choice in this trial!")
        else:
            raise ValueError("There's no choice in this trial!")

<<<<<<< HEAD
=======

>>>>>>> 56d5c669cd40f00458aeb689625709c0bf48ea12
    def __get_num_incorrects(self, time_cond):
        incorrect_trials = self.beh_msg['type'] == "ChoiceSelectionIncorect"
        incorrect = sum(np.logical_and(incorrect_trials, time_cond))
        return incorrect

    def __get_num_corrects(self, time_cond):
        correct_trials = self.beh_msg['type'] == "ChoiceSelectionCorrect"
        correct = sum(np.logical_and(correct_trials, time_cond))
        return correct


<<<<<<< HEAD

class NoiseChanceField(StimSpecDataField):
    def __init__(self, beh_msg, stim_spec):
        self.name = "NoiseChance"
        super().__init__(beh_msg, stim_spec)

    def retrieveValue(self, when):
        stim_spec_data_dict = self.retrieve_spec_data(when)
        trialtype = list(stim_spec_data_dict.keys())[0]
        noise_chance_dict =  stim_spec_data_dict[trialtype]['noiseParameters']['noiseChanceBounds']
        # noise_chance = (noise_chance_dict['lowerLim'], noise_chance_dict['upperLim'])
        self.value = noise_chance_dict


class PsychometricIdField(StimSpecDataField):
    def __init__(self, beh_msg, stim_spec):
        self.name = "PsychometricId"
        super().__init__(beh_msg, stim_spec)

    def retrieveValue(self, when):
        stim_spec_data_dict = self.retrieve_spec_data(when)
        trialtype = list(stim_spec_data_dict.keys())[0]
        try:
            psychometric_ids_dict = stim_spec_data_dict[trialtype]['psychometricIds']
            self.value = psychometric_ids_dict['setId'] + "_" + psychometric_ids_dict['stimId']
        except:
            self.value = 'None'


if __name__ == '__main__':
    save_dir = "compiled/"

    # Get DB Tables
    print("Reading Database")
    conn = connection.Connection("allen_estimshape_train_220725")
    collector = trialcollector.TrialCollector(conn)
    today_beh_msg = conn.beh_msg
    today_stim_spec = conn.stim_spec

    # Spot to save them

    # Trial Collector -> trialList
    print("Collecting Trials")
    trial_whens = collector.collect_choice_trials()
    trialList = []
    for wen in trial_whens:
        trialList.append(tf.Trial(wen))

    # Defining Fields we want
    print("Assigning Fields")
    fieldList = tf.FieldList()
    fieldList.append(TrialTypeField(today_beh_msg, today_stim_spec))
    fieldList.append(IsCorrectField(today_beh_msg))
    fieldList.append(PsychometricIdField(today_beh_msg, today_stim_spec))
    fieldList.append(NoiseChanceField(today_beh_msg, today_stim_spec))
=======
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    beh_msg = trialcollector.beh_msg
    trial_whens = trialcollector.collect_choice_trials()
    trialList = []
    for when in trial_whens:
        trialList.append(tf.Trial(when))

    fieldList = tf.FieldList()
    fieldList.append(IsCorrectField(beh_msg))

>>>>>>> 56d5c669cd40f00458aeb689625709c0bf48ea12
    for t in trialList:
        t.set_fields(fieldList)

    data = []

<<<<<<< HEAD
    for i, t in enumerate(trialList):
        print("working on " + str(i) + " out of " + str(len(trialList)))
        data = t.append_to_data(data)

    df = pd.DataFrame(data)


    #CSV SAVING
    filename = str(datetime.date.today()) + ".csv"
    path = save_dir + filename
    # existing_data = pd.read_csv(path)

    df.to_csv(path)

=======
    for t in trialList:
        data = t.append_to_data(data)

    df = pd.DataFrame(data)
    print(sum(df["IsCorrect"])/len(df.index))
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
>>>>>>> 56d5c669cd40f00458aeb689625709c0bf48ea12

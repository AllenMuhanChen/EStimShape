import os
import pickle

import pandas as pd


def main():
    round_one = ["1695315358701557_230921_125600.pk1",
                 "1695317141694062_230921_132542.pk1"]
    round_two = ["1695750887746673_230926_135448.pk1",
                 "1695752670826611_230926_142431.pk1"]
    round_three = ["1695753967774247_230926_144608.pk1",
                   "1695755745068500_230926_151545.pk1"]
    round_four = ["1695324049218232_230921_152049.pk1",
                  "1695325515951716_230921_154516.pk1"]
    round_five = ["1695326404335201_230921_160004.pk1"]

    experiment_data_filenames = round_three

    experiment_names = [experiment_data_filename.split(".")[0] for experiment_data_filename in
                        experiment_data_filenames]
    file_paths = ["/home/r2_allen/git/EStimShape/EStimShapeAnalysis/compiled/julie/%s" % experiment_data_filename for
                  experiment_data_filename in experiment_data_filenames]

    data = add_pickled_dataframes(file_paths)
    print("Combined Dataframe number of trials:", len(data))
    combined_filename = "&".join(experiment_names) + ".pk1"
    save_dir = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/compiled/julie"
    save_path = os.path.join(save_dir, combined_filename)
    data.to_pickle(save_path)


def add_pickled_dataframes(paths):
    result = None

    for path in paths:
        with open(path, 'rb') as file:
            data = pickle.load(file)
            if result is None:
                result = data
            else:
                # Concatenate the DataFrames vertically (later ones below earlier ones)
                result = pd.concat([result, data], axis=0, ignore_index=True)

    return result


if __name__ == '__main__':
    main()
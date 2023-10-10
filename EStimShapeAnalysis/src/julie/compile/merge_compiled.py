import os
import pickle

import pandas as pd


def main():
    round_one = ["1696529435680284_231005_141036.pk1",
                 "1696530952902561_231005_143553.pk1",
                 "1696531607057233_231005_144647.pk1"]
    round_two = ["1696888890257195_231009_180130_round2_1.pk1",
                 "1696891705894032_231009_184826_round2_2.pk1"]
    round_three = ["1696440834320912_231004_133354.pk1",
                   "1696441588991973_231004_134629.pk1"]
    round_four = ["1696367719246571_231003_171519.pk1",
                  "1696369421224313_231003_174341.pk1"]
    round_five = ["1695326404335201_230921_160004.pk1"]

    experiment_data_filenames = round_two

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

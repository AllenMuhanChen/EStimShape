import os
import pickle

import pandas as pd


def main():
    round_one = ["1695232474891270_230920_135436.pk1",
                 "1695234027638670_230920_142028.pk1"]
    round_two = ["1695235028758768_230920_143709.pk1",
                 "1695236893646702_230920_150814.pk1"]
    round_three = ["1695237446722197_230920_151727.pk1",
                   "1695239087935739_230920_154448.pk1"]
    round_four = ["1695239684850284_230920_155445.pk1"]
    round_five = ["1695241340595740_230920_162221.pk1"]

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

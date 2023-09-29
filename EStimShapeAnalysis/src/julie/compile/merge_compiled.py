import os
import pickle

import pandas as pd


def main():
    round_one = ["1696006131701656_230929_124853.pk1",
                 "1696006848799165_230929_130049.pk1",
                 "1696007509945401_230929_131150.pk1"]
    round_two = ["1696009164430375_230929_133924.pk1",
                 "1696010910580580_230929_140831.pk1"]
    round_three = ["1696011663436717_230929_142103.pk1",
                   "1696013332601382_230929_144853.pk1"]
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

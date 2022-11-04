import pandas
import pandas as pd
import numpy as np
import matplotlib.pylab as plt
import xmltodict
import ast

from src.compile import psychometric_compile

if __name__ == '__main__':


    to_read = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/compiled/psychometric-2022-11-04.csv"
    df = pandas.read_csv(to_read)

    df_psychometric = df[df['TrialType'] == 'Psychometric']

    # ids = df_psychometric['PsychometricId'].unique()
    ids=["1667577485864219_0", "1667577485864219_1"]
    noises = df_psychometric['NoiseChance'].unique()


    noises.sort()
    noises = noises[::-1]

    noises = [ast.literal_eval(noise) for noise in noises]

    plot_data_percent_correct = {}
    plot_data_num_trials = {}
    plot_data_num_correct = {}
    for id in ids:
        single_plot_data_percent_correct = []
        single_plot_data_num_trials = []
        single_plot_data_num_correct = []
        for noise in noises:
            trials = [row['IsCorrect'] for index, row in df_psychometric.iterrows() if row['PsychometricId'] == id and row['NoiseChance'] == str(noise)]
            totalNum = len(trials)
            correct = sum(trials)
            try:
                percent_correct = correct / totalNum
            except:
                percent_correct = 0
            single_plot_data_percent_correct.append(percent_correct)
            single_plot_data_num_trials.append(totalNum)
            single_plot_data_num_correct.append(correct)
        plot_data_percent_correct[id] = single_plot_data_percent_correct
        plot_data_num_trials[id] = single_plot_data_num_trials
        plot_data_num_correct[id] = single_plot_data_num_correct
    print(plot_data_percent_correct)
    print(pd.DataFrame(plot_data_percent_correct))

    noises_upper_lims = [noise['upperLim'] for noise in noises]
    x_axis = noises_upper_lims

    for id in ids:
        y_axis = plot_data_percent_correct[id]
        plt.plot(x_axis, y_axis, marker='o', label=id)

        # LABEL PLOT
        for x,y, num_correct, num_total in zip(x_axis, y_axis, plot_data_num_correct[id], plot_data_num_trials[id]):
            plt.text(x, y, "%d/%d = %.2f" % (num_correct, num_total, y))
    plt.legend()

    plt.show()

    numCorrect = sum(df_psychometric['IsCorrect'])
    totalNum = len(df_psychometric.index)

    plot_data_percent_correct = numCorrect / totalNum

    print(plot_data_percent_correct)

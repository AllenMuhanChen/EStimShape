import pandas
import pandas as pd
import matplotlib.pylab as plt
import ast

if __name__ == '__main__':


    to_read = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/compiled/psychometric-2022-11-11.csv"
    df = pandas.read_csv(to_read)

    df_rand = df[df['TrialType'] == 'Rand']


    # ids=["1667843144454282_0", "1667843144454282_1"]
    noises = df_rand['NoiseChance'].unique()


    noises.sort()
    noises = noises[::-1]

    noises = [ast.literal_eval(noise) for noise in noises]

    plot_data_percent_correct = {}
    plot_data_num_trials = {}
    plot_data_num_correct = {}

    plot_data_percent_correct = []
    plot_data_num_trials = []
    plot_data_num_correct = []
    for noise in noises:
        trials = [row['IsCorrect'] for index, row in df_rand.iterrows() if row['NoiseChance'] == str(noise)]
        totalNum = len(trials)
        correct = sum(trials)
        try:
            percent_correct = correct / totalNum
        except:
            percent_correct = 0
        plot_data_percent_correct.append(percent_correct)
        plot_data_num_trials.append(totalNum)
        plot_data_num_correct.append(correct)



    print(plot_data_percent_correct)
    print(pd.DataFrame(plot_data_percent_correct))

    noises_upper_lims = [noise['upperLim'] for noise in noises]
    x_axis = noises_upper_lims


    y_axis = plot_data_percent_correct
    plt.plot(x_axis, y_axis, marker='o')

    # LABEL PLOT
    for x,y, num_correct, num_total in zip(x_axis, y_axis, plot_data_num_correct, plot_data_num_trials):
        plt.text(x, y, "%d/%d = %.2f" % (num_correct, num_total, y))
    plt.legend()

    plt.show()

    numCorrect = sum(df_rand['IsCorrect'])
    totalNum = len(df_rand.index)

    plot_data_percent_correct = numCorrect / totalNum

    print(plot_data_percent_correct)

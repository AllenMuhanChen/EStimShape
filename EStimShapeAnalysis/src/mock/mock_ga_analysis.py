from __future__ import annotations

from matplotlib import pyplot as plt
from matplotlib.pyplot import subplots

from src.compile.classic_database_fields import GaTypeField, GaLineageField, StimSpecIdField, StimSpecDataField, \
    StimSpecField
from src.compile.trial_field import FieldList, get_data_from_trials
from src.mock.mock_ga_responses import collect_trials
from src.mock.mock_rwa_analysis import MockResponseField
from src.util import time_util
from src.util.connection import Connection
from src.util.time_util import When


def show_top_n(data, n):
    n_rows = int(n**0.5)
    n_cols = int(n/n_rows)
    if n_rows * n_cols < n:
        n_cols += 1
    fig, axes = subplots(n_rows, n_cols)
    for (i, row), axis in zip(data.head(n).iterrows(), axes.flatten()):
        img = plt.imread(row["Path"])
        axis.imshow(img)
        axis.set_title(row["Response"])

    plt.show()

def main():
    """example of data analysis pipeline"""

    # PARAMETERS
    conn = Connection("allen_estimshape_dev_221110")

    # PIPELINE
    trial_tstamps = collect_trials(conn, time_util.all())
    data = compile_data(conn, trial_tstamps)
    data = sort_by_response(data)

    # PLOTTING
    show_top_n(data, 10)

    print(data.to_string())


class PngPathField(StimSpecField):
    def get(self, when: When):
        stim_spec = super().get(when)
        return stim_spec["StimSpec"]["path"]


def compile_data(conn, trial_tstamps):
    fields = FieldList()
    fields.append(GaTypeField(conn, "GaType"))
    fields.append(GaLineageField(conn, "Lineage"))
    fields.append(StimSpecIdField(conn, "Id"))
    fields.append(MockResponseField(conn, 1, "Response"))
    fields.append(PngPathField(conn, "Path"))

    return get_data_from_trials(fields, trial_tstamps)


def sort_by_response(data):
    data = data.sort_values(by="Response", ascending=False)
    return data


if __name__ == '__main__':
    main()

from analysis.nafc.nafc_database_fields import IsCorrectField, NoiseChanceField
from clat.compile.trial.trial_collector import TrialCollector
from clat.compile.trial.trial_field import FieldList
from clat.util import time_util
from clat.util.connection import Connection
from clat.util.time_util import When


def collect_choice_trials(conn: Connection, when: When = time_util.all()) -> list[When]:
    trial_collector = TrialCollector(conn, when)
    return trial_collector.collect_choice_trials()

def main():
    conn = Connection("allen_estimshape_train_231211")
    trial_tstamps = collect_choice_trials(conn, time_util.all())

    fields = FieldList()
    fields.append(IsCorrectField(conn))
    fields.append(NoiseChanceField(conn))

    data = fields.get_data(trial_tstamps)
    print(data.to_string())

if __name__ == '__main__':
    main()
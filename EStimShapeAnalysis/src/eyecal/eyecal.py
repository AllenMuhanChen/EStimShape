from src.compile import trial_collector
from src.util.connection import Connection
from src.util import time_util
database = "allen_estimshape_train_220725"

if __name__ == '__main__':
    conn = Connection(database, when=time_util.all())
    collector = trial_collector.TrialCollector(conn)
    print(collector.collect_trials())



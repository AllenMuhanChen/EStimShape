import pandas as pd

from clat.compile.trial.cached_fields import CachedFieldList
from clat.compile.trial.classic_database_fields import StimSpecDataField
from clat.intan.one_file_spike_parsing import OneFileParser
from clat.util.connection import Connection
from clat.util.time_util import When
from src.analysis.ga.fields import TaskIdField, StimIdField
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context


def compile_data(conn: Connection, trial_tstamps: list[When]) -> pd.DataFrame:
    # set up way to parse here? We may need to parse multiple files?
    parser = MultiFileParser()


    fields = CachedFieldList()
    fields.append(TaskIdField(conn))
    fields.append(StimIdField(conn))


    data = fields.to_data(trial_tstamps)
    return data

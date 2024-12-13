import numpy as np
import xmltodict
from clat.compile.trial.cached_fields import CachedDatabaseField
from clat.compile.trial.classic_database_fields import StimSpecIdField
from clat.util.connection import Connection
from clat.util.time_util import When

from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.startup import context


class TaskIdField(CachedDatabaseField):
    def get(self, when: When) -> int:
        try:
            self.conn.execute(
                "SELECT msg from BehMsg WHERE "
                "type = 'SlideOn' AND "
                "tstamp >= %s AND tstamp <= %s",
                params=(int(when.start), int(when.stop)))
            trial_msg_xml = self.conn.fetch_one()
            trial_msg_dict = xmltodict.parse(trial_msg_xml)
            taskId = int(trial_msg_dict['SlideEvent']['taskId'])

            return taskId
        except:
            return "None"

    def get_name(self):
        return "TaskId"


class StimIdField(TaskIdField):
    def get(self, when: When) -> int:
        task_id = self.get_cached_super(when, TaskIdField)
        self.conn.execute("SELECT stim_id from TaskToDo WHERE "
                          "task_id = %s",
                          params=(task_id,))
        stim_spec_id = self.conn.fetch_one()
        return stim_spec_id

    def get_name(self):
        return "StimId"


class LineageField(StimIdField):
    def get(self, when: When) -> str:
        stim_spec_id = self.get_cached_super(when, StimIdField)

        self.conn.execute("SELECT lineage_id FROM StimGaInfo WHERE"
                          " stim_id = %s",
                          params=(stim_spec_id,))

        lineage = self.conn.fetch_one()
        return lineage

    def get_name(self):
        return "Lineage"


class RegimeField(LineageField):
    def get(self, when: When) -> str:
        lineage_id = self.get_cached_super(when, LineageField)
        self.conn.execute("SELECT regime FROM LineageGaInfo WHERE lineage_id"
                          " = %s ORDER BY gen_id DESC LIMIT 1",
                          params=(lineage_id,))
        regime = self.conn.fetch_one()
        return regime

    def get_name(self):
        return "Regime"


class ClusterResponseField(StimIdField):

    def __init__(self, conn: Connection):
        super().__init__(conn)
        self.db_util = MultiGaDbUtil(conn)
        self.cluster_channels = self.db_util.read_current_cluster(context.ga_name)

    def get(self, when: When) -> list:
        task_id = self.get_cached_super(when, TaskIdField)
        all_responses = []
        for cluster_channel in self.cluster_channels:
            self.conn.execute("SELECT spikes_per_second FROM ChannelResponses WHERE task_id = %s AND channel=%s",
                              [task_id, cluster_channel.value])
            responses = self.conn.fetch_all()
            all_responses.extend([float(response[0]) for response in responses])

        return all_responses

    def get_name(self):
        return "Cluster Responses"

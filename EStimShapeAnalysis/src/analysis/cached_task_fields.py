import os

import xmltodict

from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.util.connection import Connection
from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.startup import context


class LineageField(StimSpecIdField):
    def get(self, task_id) -> str:
        stim_spec_id = self.get_cached_super(task_id, StimSpecIdField)

        self.conn.execute("SELECT lineage_id FROM StimGaInfo WHERE"
                          " stim_id = %s",
                          params=(stim_spec_id,))

        lineage = self.conn.fetch_one()
        return lineage

    def get_name(self):
        return "Lineage"

class StimTypeField(StimSpecIdField):

    def get(self, task_id) -> str:
        stim_spec_id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT stim_type FROM StimGaInfo WHERE stim_id = %s",
                          params=(stim_spec_id,))
        stim_type = self.conn.fetch_one()
        return stim_type

    def get_name(self):
        return "StimType"

class StimPathField(StimSpecIdField):
    def get(self, task_id) -> str:
        stim_id = self.get_cached_super(task_id, StimSpecIdField)

        # Get StimSpec XML
        self.conn.execute("SELECT spec FROM StimSpec WHERE id = %s", (stim_id,))
        stim_spec_xml = self.conn.fetch_one()

        if stim_spec_xml:
            # Parse XML to dict
            stim_spec_dict = xmltodict.parse(stim_spec_xml)
            path = stim_spec_dict['StimSpec']['path']

            # Clean path - remove sftp prefix
            if 'sftp:host=' in path:
                path = path[path.find('/home/'):]

            return path
        return None

    def get_name(self):
        return "StimPath"

class ThumbnailField(StimSpecIdField):
    def get(self, task_id) -> str:
        stim_id = self.get_cached_super(task_id, StimSpecIdField)

        # Get StimSpec XML
        self.conn.execute("SELECT spec FROM StimSpec WHERE id = %s", (stim_id,))
        stim_spec_xml = self.conn.fetch_one()

        if stim_spec_xml:
            # Parse XML to dict
            stim_spec_dict = xmltodict.parse(stim_spec_xml)
            path = stim_spec_dict['StimSpec']['path']

            # Clean path - remove sftp prefix
            if 'sftp:host=' in path:
                path = path[path.find('/home/'):]
            # Add thumbnail suffix before .png
            if path.endswith('.png'):
                thumbnail_path = path[:-4] + '_thumbnail.png'
                if os.path.exists(thumbnail_path):
                    return thumbnail_path
                else:
                    return path

        return None

    def get_name(self):
        return "ThumbnailPath"


class GAResponseField(StimSpecIdField):
    def get(self, task_id) -> float:
        stim_spec_id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT response FROM StimGaInfo WHERE stim_id = %s",
                          params=(stim_spec_id,))
        ga_response = self.conn.fetch_all()
        return float(ga_response[0][0])

    def get_name(self):
        return "GA Response"


class ParentIdField(StimSpecIdField):
    def get(self, task_id) -> float:
        stim_spec_id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT parent_id FROM StimGaInfo WHERE stim_id = %s",
                          params=(stim_spec_id,))
        ga_response = self.conn.fetch_all()
        return float(ga_response[0][0])

    def get_name(self):
        return "ParentId"

class ClusterResponseField(StimSpecIdField):

    def __init__(self, conn: Connection, cluster_combination_strategy):
        super().__init__(conn)
        self.db_util = MultiGaDbUtil(conn)
        self.cluster_channels = self.db_util.read_current_cluster(context.ga_name)
        self.cluster_combination_strategy = cluster_combination_strategy

    def get(self, task_id) -> list:
        all_responses = []
        for cluster_channel in self.cluster_channels:
            self.conn.execute("SELECT spikes_per_second FROM ChannelResponses WHERE task_id = %s AND channel=%s",
                              [task_id, cluster_channel.value])
            responses = self.conn.fetch_all()
            all_responses.extend([float(response[0]) for response in responses])

        return self.cluster_combination_strategy(all_responses)

    def get_name(self):
        return "Cluster Response"


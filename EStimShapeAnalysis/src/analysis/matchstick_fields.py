from __future__ import annotations

import xmltodict

from clat.compile.task.cached_task_fields import CachedTaskDatabaseField
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.tstamp.classic_database_tstamp_fields import StimIdField


class MatchStickField(CachedTaskDatabaseField):
    def __init__(self, conn, mstick_spec_data_source):
        super().__init__(conn)
        self.mstick_spec_source = mstick_spec_data_source

    def get(self, task_id: int) -> dict:
        return self.mstick_spec_source.get(task_id)

    def get_name(self):
        return "MatchStickData"


class ShaftField(MatchStickField):
    def get(self, task_id: int) -> list[dict]:
        mstick_data = self.get_cached_super(task_id, MatchStickField, self.mstick_spec_source)
        shaft_data = mstick_data["AllenMStickData"]['shaftData']['ShaftData']
        return shaft_data

    def get_name(self):
        return "Shaft"


class TerminationField(MatchStickField):
    def get(self, task_id: int) -> list[dict]:
        mstick_data = self.get_cached_super(task_id, MatchStickField, self.mstick_spec_source)
        termination_data = mstick_data["AllenMStickData"]['terminationData']['TerminationData']
        return termination_data

    def get_name(self):
        return "Termination"


class JunctionField(MatchStickField):
    def get(self, task_id: int) -> list[dict]:
        mstick_data = self.get_cached_super(task_id, MatchStickField, self.mstick_spec_source)
        junction_data = mstick_data["AllenMStickData"]['junctionData']['JunctionData']

        # We don't need these for RWA so let's remove them
        if isinstance(junction_data, list):
            for junction in junction_data:
                del junction['id']
                del junction['connectedCompIds']
        else:
            del junction_data['id']
            del junction_data['connectedCompIds']

        return junction_data

    def get_name(self):
        return "Junction"


class StimSpecDataField(StimSpecIdField):
    def get(self, task_id: int) -> dict:
        stim_spec_id = super().get(task_id)
        self.conn.execute("SELECT data from StimSpec WHERE "
                          "id = %s",
                          params=(stim_spec_id,))

        stim_spec_data_xml = self.conn.fetch_one()
        stim_spec_data_dict = xmltodict.parse(stim_spec_data_xml)
        return stim_spec_data_dict


class AllenMStickDataField(StimSpecDataField):
    def get(self, task_id: int) -> dict:
        stim_spec_data = self.get_cached_super(task_id, StimSpecDataField)
        return xmltodict.parse(stim_spec_data)

    def get_name(self):
        return "AllenMStickData"

import xmltodict

from compile.task.base_database_fields import StimSpecDataField
from util.connection import Connection


class MatchStickField(StimSpecDataField):
    def __init__(self, conn: Connection, name: str = None):
        super().__init__(conn, name)

    def get_mstick_data(self, task_id: int) -> dict:
        stim_spec_data_xml = super().get(task_id)
        stim_spec_data = xmltodict.parse(stim_spec_data_xml)
        # Assuming the mstick_data is part of the stim_spec_data, extract it
        mstick_data = stim_spec_data["AllenMStickData"]
        return mstick_data


class ShaftField(MatchStickField):
    def get(self, task_id: int) -> list[dict]:
        mstick_data = self.get_mstick_data(task_id)
        shaft_data = mstick_data['shaftData']['ShaftData']
        return shaft_data


class TerminationField(MatchStickField):
    def get(self, task_id: int) -> list[dict]:
        mstick_data = self.get_mstick_data(task_id)
        termination_data = mstick_data['terminationData']['TerminationData']
        return termination_data


class JunctionField(MatchStickField):
    def get(self, task_id: int) -> list[dict]:
        mstick_data = self.get_mstick_data(task_id)
        junction_data = mstick_data['junctionData']['JunctionData']
        return junction_data

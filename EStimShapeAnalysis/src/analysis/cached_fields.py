import os

import xmltodict
from clat.compile.tstamp.classic_database_tstamp_fields import StimSpecIdField, TaskIdField, StimIdField
from clat.util.connection import Connection
from clat.util.time_util import When

from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.startup import context


class StimSpecDataField(StimSpecIdField):
    def get(self, when: When) -> dict:
        stim_spec_id = super().get(when)
        self.conn.execute("SELECT data from StimSpec WHERE "
                          "id = %s",
                          params=(stim_spec_id,))

        stim_spec_data_xml = self.conn.fetch_one()
        stim_spec_data_dict = xmltodict.parse(stim_spec_data_xml)
        return stim_spec_data_dict











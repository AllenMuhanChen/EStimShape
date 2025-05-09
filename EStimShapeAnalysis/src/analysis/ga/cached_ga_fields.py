from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.tstamp.classic_database_tstamp_fields import get_new_ga_lineage_from_stim_spec_id, \
    get_regime_score_from_lineage_id


class LineageField(StimSpecIdField):
    def get(self, task_id) -> int:
        stim_spec_id = self.get_cached_super(task_id, StimSpecIdField)

        self.conn.execute("SELECT lineage_id FROM StimGaInfo WHERE"
                          " stim_id = %s",
                          params=(stim_spec_id,))

        lineage = self.conn.fetch_one()
        return int(lineage)

    def get_name(self):
        return "Lineage"


class RegimeScoreField(LineageField):
    def get(self, task_id: int) -> float:
        lineage_id = self.get_cached_super(task_id, LineageField)
        return float(get_regime_score_from_lineage_id(self.conn, lineage_id))

    def get_name(self):
        return "RegimeScore"


class GAResponseField(StimSpecIdField):
    def get(self, task_id) -> float:
        stim_spec_id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT response FROM StimGaInfo WHERE stim_id = %s",
                          params=(stim_spec_id,))
        ga_response = self.conn.fetch_all()
        if not ga_response:
            raise ValueError(f"No GA response found for stim_spec_id {stim_spec_id}")
        return float(ga_response[0][0])

    def get_name(self):
        return "GA Response"


class ParentIdField(StimSpecIdField):
    def get(self, task_id) -> int:
        stim_spec_id = self.get_cached_super(task_id, StimSpecIdField)
        self.conn.execute("SELECT parent_id FROM StimGaInfo WHERE stim_id = %s",
                          params=(stim_spec_id,))
        ga_response = self.conn.fetch_all()
        return int(ga_response[0][0])

    def get_name(self):
        return "ParentId"

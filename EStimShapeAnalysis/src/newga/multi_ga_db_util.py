import xmltodict

from intan.channels import Channel
from util.connection import Connection


class MultiGaDbUtil:
    def __init__(self, connection: Connection):
        self.conn = connection

    def read_ready_gas_and_generations_info(self):
        name = "task_to_do_ga_and_gen_ready"

        self.conn.execute("SELECT val FROM InternalState WHERE name = %s", (name,))
        xml = self.conn.fetch_one()
        if xml is None:
            raise Exception(f"Could not find internal state {name}")

        return MultiGaGenerationInfo.from_xml(xml).gen_id_for_ga

    def update_ready_gas_and_generations_info(self, ga_name: str, gen_id: int):
        name = "task_to_do_ga_and_gen_ready"

        self.conn.execute("SELECT val FROM InternalState WHERE name = %s", (name,))
        xml = self.conn.fetch_one()
        if xml is None:
            raise Exception(f"Could not find internal state {name}")
        else:
            gen_id_for_ga = MultiGaGenerationInfo.from_xml(xml)
            gen_id_for_ga.gen_id_for_ga[ga_name] = gen_id
            xml = gen_id_for_ga.to_xml()

        self.conn.execute("UPDATE InternalState SET val = %s WHERE name = %s", (xml, name))

    def write_lineage_ga_info(self, lineage_id: int, tree_spec: str, lineage_data: str, gen_id: int, regime: str):
        self.conn.execute(
            "INSERT INTO LineageGaInfo (lineageId, treeSpec, lineageData, gen_id, regime) VALUES (%s, %s, %s, %s, %s)",
            (lineage_id, tree_spec, lineage_data, gen_id, regime))

    def read_lineage_ids_for_experiment_id(self, experiment_id: int) -> list[int]:
        self.conn.execute("SELECT lineageId FROM LineageGaInfo WHERE experimentId = %s", (experiment_id,))
        return self.conn.fetch_all()

    def read_regime_for_lineage(self, lineage_id: int) -> str:
        self.conn.execute(
            "SELECT regime FROM LineageGaInfo WHERE lineage_id = %s",
            (lineage_id,)
        )
        regime_str = self.db_util.conn.fetch_one()
        return regime_str

    def write_stim_ga_info(self, stim_id: int, parent_id: int, ga_name: str, gen_id: int, lineage_id: int,
                           stim_type: str):
        self.conn.execute(
            "INSERT IGNORE INTO StimGaInfo (stimId, parentId, gaName, genId, lineageId, stimType) VALUES (%s, %s, %s, %s, %s, %s)",
            (stim_id, parent_id, ga_name, gen_id, lineage_id, stim_type))

    def read_task_done_ids_for_stim_id(self, ga_name: str, stim_id: int):
        self.conn.execute(
            "SELECT d.task_id "
            "FROM TaskDone d "
            "JOIN TaskToDo t ON d.task_id = t.task_id "
            "WHERE t.ga_name = %s AND t.stim_id = %s",
            (ga_name, stim_id))

        rows = self.conn.fetch_all()
        task_ids = [row[0] for row in rows]

        return task_ids

    def read_stims_with_no_responses(self, ga_name: str):
        self.conn.execute(
            "SELECT s.stim_id "
            "FROM StimGaInfo s "
            "LEFT JOIN StimResponses r ON s.stim_id = r.stim_id "
            "WHERE r.stim_id IS NULL AND s.ga_name = %s", (ga_name,))

        rows = self.conn.fetch_all()
        stim_ids = [row[0] for row in rows]

        return stim_ids

    def add_stim_response(self, stim_id: int, task_id: int, channel: str, spikes_per_second: float):
        self.conn.execute(
            "INSERT INTO StimResponses (stim_id, task_id, channel, spikes_per_second) VALUES (%s, %s, %s, %s)",
            (stim_id, task_id, channel, spikes_per_second))

    def read_stims_with_no_driving_response(self):
        self.conn.execute(
            "SELECT stim_id "
            "FROM StimGaInfo "
            "WHERE response IS NULL OR response = ''")

        rows = self.conn.fetch_all()
        stim_ids = [row[0] for row in rows]

        return stim_ids

    def update_driving_response(self, stim_id: int, response: float):
        self.conn.execute(
            "UPDATE StimGaInfo SET response = %s WHERE stim_id = %s",
            (response, stim_id))

    def read_driving_response(self, stim_id: int):
        self.conn.execute(
            "SELECT response "
            "FROM StimGaInfo "
            "WHERE stim_id = %s",
            (stim_id,))

        response = self.conn.fetch_one()

        return response

    def read_experiment_id(self, experiment_name):
        self.conn.execute("SELECT experiment_id FROM CurrentExperiments WHERE experiment_name = %s", (experiment_name,))
        experiment_id = self.conn.fetch_one()
        if experiment_id is None:
            raise Exception(f"Could not find experiment with name {experiment_name}")
        return experiment_id

    def update_experiment_id(self, experiment_name, experiment_id):
        self.conn.execute("UPDATE CurrentExperiments SET experiment_id = %s WHERE experiment_name = %s",
                          (experiment_id, experiment_name))

    def read_channels(self, experiment_id, gen_id):
        self.conn.execute("SELECT channel FROM ClusterInfo WHERE experiment_id = %s AND gen_id = %s",
                          (experiment_id, gen_id))
        rows = self.conn.fetch_all()
        channels = [row[0] for row in rows]
        return channels

    def read_current_cluster(self, ga_name) -> list[Channel]:
        # Get current experiment_id
        current_experiment_id = self.read_experiment_id(ga_name)

        self.conn.execute("SELECT MAX(gen_id) FROM ClusterInfo WHERE experiment_id = %s",
                          (current_experiment_id,))
        most_recent_gen_id = self.conn.fetch_one()
        if most_recent_gen_id is None:
            raise Exception(f"Could not find gen_id for experiment_id {current_experiment_id}")

        # select the current cluster by grouping largest gen_id
        cluster_as_strings = self.read_channels(current_experiment_id, most_recent_gen_id)
        cluster = [Channel[channel_as_string] for channel_as_string in cluster_as_strings]
        return cluster

    def read_responses_for(self, stim_id, channel=None):
        if channel is None:
            self.conn.execute("SELECT spikes_per_second FROM StimResponses WHERE stim_id = %s", (stim_id,))
        else:
            self.conn.execute("SELECT spikes_per_second FROM StimResponses WHERE stim_id = %s AND channel = %s",
                              (stim_id, channel))
        rows = self.conn.fetch_all()
        spikes_per_second_list = [row[0] for row in rows]
        return spikes_per_second_list

    def read_stim_ids_for_lineage(self, lineage_id):
        self.conn.execute("SELECT stim_id FROM StimGaInfo WHERE lineage_id = %s", (lineage_id,))
        rows = self.conn.fetch_all()
        stim_ids = [row[0] for row in rows]
        return stim_ids


class MultiGaGenerationInfo:
    def __init__(self, gen_id_for_ga=None):
        self.gen_id_for_ga = gen_id_for_ga or {}

    @classmethod
    def from_xml(cls, xml):
        data = xmltodict.parse(xml)
        entry_data = data['GenerationInfo']['genIdForGA']['entry']
        # If there is only one entry, convert it to a list for consistency
        if isinstance(entry_data, dict):
            entry_data = [entry_data]
        gen_id_for_ga = {entry['string']: int(entry['long']) for entry in entry_data}
        return cls(gen_id_for_ga)

    def to_xml(self):
        data = {'GenerationInfo':
                    {'genIdForGA':
                         {'entry': [{'string': k, 'long': str(v)} for k, v in self.gen_id_for_ga.items()]}}}
        return xmltodict.unparse(data, pretty=True)

from __future__ import annotations

import math
from collections import namedtuple
from dataclasses import dataclass, Field
from typing import List, Tuple, Any

import xmltodict
from numpy import float64

from clat.intan.channels import Channel
from clat.util.connection import Connection


class MultiGaDbUtil:
    conn: Connection

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

    def write_lineage_ga_info(self, lineage_id: int, tree_spec: str, lineage_data: str, experiment_id: int, gen_id: int,
                              regime: str):
        self.conn.execute(
            "INSERT INTO LineageGaInfo (lineage_id, tree_spec, lineage_data, experiment_id, gen_id, regime) VALUES (%s, %s, %s, %s, %s, %s)",
            (lineage_id, tree_spec, lineage_data, experiment_id, gen_id, regime))

    def read_lineage_ids_for_experiment_id(self, experiment_id: int) -> list[int]:
        self.conn.execute("SELECT lineage_id FROM LineageGaInfo WHERE experiment_id = %s", (experiment_id,))
        lineage_ids_as_tuples = self.conn.fetch_all()
        return [lineage_id_as_tuple[0] for lineage_id_as_tuple in lineage_ids_as_tuples]

    def read_regime_for_lineage(self, lineage_id: int) -> str:
        self.conn.execute(
            "SELECT regime FROM LineageGaInfo WHERE lineage_id = %s",
            (lineage_id,)
        )
        regime_str = self.db_util.conn.fetch_one()
        return regime_str

    def read_lineage_ga_info_for_experiment_id_and_gen_id(self, experiment_id: int, gen_id: int) -> list[
        LineageGaInfoEntry]:
        self.conn.execute(
            "SELECT lineage_id, tree_spec, regime, lineage_data FROM LineageGaInfo WHERE experiment_id = %s AND gen_id = %s",
            (experiment_id, gen_id)
        )
        rows = self.conn.fetch_all()
        output = []
        for row in rows:
            lineage_id, tree_spec, regime, lineage_data = row
            output.append(
                LineageGaInfoEntry(lineage_id=lineage_id, tree_spec=tree_spec, regime=regime, lineage_data=lineage_data,
                                   gen_id=gen_id, experiment_id=experiment_id))
        return output

    def write_stim_ga_info(self, *, stim_id: int, parent_id: int, lineage_id: int,
                           stim_type: str, mutation_magnitude: float, gen_id: int):
        self.conn.execute(
            "INSERT IGNORE INTO StimGaInfo (stim_id, parent_id, lineage_id, stim_type, mutation_magnitude, gen_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (stim_id, parent_id, lineage_id, stim_type, mutation_magnitude, gen_id))

    def read_stim_ga_info_entry(self, stim_id: int) -> StimGaInfoEntry:
        def float_or_none(val: Any):
            if val is None:
                return None
            else:
                return float(val)

        self.conn.execute(
            "SELECT parent_id, lineage_id, stim_type, response, mutation_magnitude, gen_id FROM StimGaInfo WHERE stim_id = %s order by gen_id desc",
            (stim_id,))
        rows = self.conn.fetch_all()
        if rows is None or len(rows) == 0:
            raise Exception(f"Could not find StimGaInfo entry for stim_id {stim_id}")
        else:
            parent_id, lineage_id, stim_type, response, mutation_magnitude, gen_id = rows[0]
            return StimGaInfoEntry(stim_id=int(stim_id), parent_id=int(parent_id),
                                   lineage_id=int(lineage_id), stim_type=str(stim_type),
                                   response=float(response), mutation_magnitude=float_or_none(mutation_magnitude),
                                   gen_id=int(gen_id))

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
        current_experiment_id = self.read_current_experiment_id(ga_name)
        lineages_for_experiment_id = self.read_lineage_ids_for_experiment_id(current_experiment_id)
        # lineages_for_experiment_id = [lineage_tuple[0] for lineage_tuple in lineages_for_experiment_id]

        placeholders = ','.join(['%s'] * len(lineages_for_experiment_id))
        query = f"""
                SELECT s.stim_id
                FROM StimGaInfo s
                LEFT JOIN ChannelResponses r ON s.stim_id = r.stim_id
                WHERE r.stim_id IS NULL AND lineage_id IN ({placeholders})
            """

        self.conn.execute(query, lineages_for_experiment_id)
        rows = self.conn.fetch_all()

        stim_ids = [row[0] for row in rows]

        return stim_ids

    def add_channel_response(self, stim_id: int, task_id: int, channel: str, spikes_per_second: float):
        self.conn.execute(
            "INSERT INTO ChannelResponses (stim_id, task_id, channel, spikes_per_second) VALUES (%s, %s, %s, %s)",
            (stim_id, task_id, channel, spikes_per_second))

    def add_channel_responses_in_batch(self, insert_data):
        cursor = self.conn.mydb.cursor()
        query = """
            INSERT INTO ChannelResponses (stim_id, task_id, channel, spikes_per_second)
            VALUES (%s, %s, %s, %s)
        """
        cursor.executemany(query, insert_data)
        self.conn.mydb.commit()
        cursor.close()

    def read_stims_with_no_driving_response(self):
        self.conn.execute(
            "SELECT stim_id "
            "FROM StimGaInfo "
            "WHERE response IS NULL OR response = ''")

        rows = self.conn.fetch_all()
        stim_ids = [row[0] for row in rows]

        return stim_ids

    def update_driving_response(self, stim_id: int, response: float):
        #if response is not float
        if math.isnan(response):
            print(f"Warning: response for stim_id {stim_id} is NaN, setting to 0")
            response = 0
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

    def read_current_experiment_id(self, experiment_name):
        self.conn.execute(
            "SELECT experiment_id FROM CurrentExperiments WHERE experiment_name = %s ORDER BY experiment_id desc",
            (experiment_name,))
        experiment_id = self.conn.fetch_one()
        if experiment_id is None:
            raise Exception(f"Could not find experiment with name {experiment_name}")
        return experiment_id

    def write_new_experiment_id(self, experiment_name, experiment_id):
        self.conn.execute("INSERT INTO CurrentExperiments (experiment_name, experiment_id) VALUES (%s, %s)",
                          (experiment_name, experiment_id))

    def read_cluster_channels(self, experiment_id, gen_id):
        self.conn.execute("SELECT channel FROM ClusterInfo WHERE experiment_id = %s AND gen_id = %s",
                          (experiment_id, gen_id))
        rows = self.conn.fetch_all()
        channels = [row[0] for row in rows]
        return channels

    def read_current_cluster(self, ga_name) -> list[Channel]:
        # Get current experiment_id
        current_experiment_id = self.read_current_experiment_id(ga_name)

        self.conn.execute("SELECT MAX(gen_id) FROM ClusterInfo WHERE experiment_id = %s",
                          (current_experiment_id,))
        most_recent_gen_id = self.conn.fetch_one()
        if most_recent_gen_id is None:
            raise Exception(f"Could not find gen_id for experiment_id {current_experiment_id}")

        # select the current cluster by grouping largest gen_id
        cluster_as_strings = self.read_cluster_channels(current_experiment_id, most_recent_gen_id)
        cluster = [Channel[channel_as_string] for channel_as_string in cluster_as_strings]
        return cluster

    def write_cluster_info(self, experiment_id: int, gen_id: int, channel: str):
        """
        Writes cluster information into the database.

        Parameters:
        - experiment_id: The identifier for the experiment.
        - gen_id: The generation identifier.
        - channel: The channel information to be recorded.

        This method will insert a new record into the ClusterInfo table with the provided
        experiment_id, gen_id, and channel.
        """
        self.conn.execute(
            "INSERT INTO ClusterInfo (experiment_id, gen_id, channel) VALUES (%s, %s, %s)",
            (experiment_id, gen_id, channel)
        )

    def read_responses_for(self, stim_id, channel: str = None):
        if channel is None:
            self.conn.execute("SELECT spikes_per_second FROM ChannelResponses WHERE stim_id = %s", (stim_id,))
        else:
            self.conn.execute("SELECT spikes_per_second FROM ChannelResponses WHERE stim_id = %s AND channel = %s",
                              (stim_id, channel))
        rows = self.conn.fetch_all()
        spikes_per_second_list = [float(row[0]) for row in rows]
        return spikes_per_second_list

    def read_stim_ids_for_lineage(self, lineage_id):
        self.conn.execute("SELECT stim_id FROM StimGaInfo WHERE lineage_id = %s", (lineage_id,))
        rows = self.conn.fetch_all()
        stim_ids = [row[0] for row in rows]
        return stim_ids


@dataclass(kw_only=True)
class LineageGaInfoEntry:
    lineage_id: int
    tree_spec: str
    lineage_data: str
    experiment_id: int
    gen_id: int
    regime: str


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


@dataclass(kw_only=True)
class StimGaInfoEntry:
    stim_id: int
    parent_id: int
    lineage_id: int
    stim_type: str
    response: float
    mutation_magnitude: float
    gen_id: int

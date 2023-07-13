import xmltodict

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

    def write_lineage_ga_info(self, lineage_id: int, tree_spec: str, lineage_data: str):
        self.conn.execute(
            "INSERT INTO LineageGaInfo (lineageId, treeSpec, lineageData) VALUES (%s, %s, %s)",
            (lineage_id, tree_spec, lineage_data))

    def write_stim_ga_info(self, stim_id: int, parent_id: int, ga_name: str, gen_id: int, lineage_id: int,
                           stim_type: str):
        self.conn.execute(
            "INSERT IGNORE INTO StimGaInfo (stimId, parentId, gaName, genId, lineageId, stimType) VALUES (%s, %s, %s, %s, %s, %s)",
            (stim_id, parent_id, ga_name, gen_id, lineage_id, stim_type))


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

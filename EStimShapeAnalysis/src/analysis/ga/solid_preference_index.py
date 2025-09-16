from typing import Optional
from clat.util.connection import Connection
from clat.pipeline.pipeline_base_classes import ComputationModule, InputT, OutputT, AnalysisModuleFactory, OutputHandler
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context


def create_sp_index_module(channel=None, session_id=None):
    index_module = AnalysisModuleFactory.create(
        computation=SolidPreferenceIndexCalculator(channel),
        output_handler=SolidPreferenceIndexDBSaver(session_id, channel)
    )
    return index_module


class SolidPreferenceIndexCalculator(ComputationModule):
    def __init__(self, response_key: str):
        self.response_key = response_key

    def compute(self, prepared_data: InputT) -> OutputT:
        # Filter for 3D and 2D test types
        data_3d = prepared_data[prepared_data['TestType'] == '3D']
        data_2d = prepared_data[prepared_data['TestType'] == '2D']

        # Analyze only the specific channel
        total_3d_rate = 0
        for _, row in data_3d.iterrows():
            spike_rates = row['Spike Rate by channel']
            if isinstance(spike_rates, dict) and self.response_key in spike_rates:
                total_3d_rate += spike_rates[self.response_key]

        total_2d_rate = 0
        for _, row in data_2d.iterrows():
            spike_rates = row['Spike Rate by channel']
            if isinstance(spike_rates, dict) and self.response_key in spike_rates:
                total_2d_rate += spike_rates[self.response_key]

        solid_preference_index = (total_3d_rate - total_2d_rate) / max(total_3d_rate, total_2d_rate)
        print(f"The Solid Preference Index of {self.response_key} is: {solid_preference_index}")
        return solid_preference_index


class SolidPreferenceIndexDBSaver(OutputHandler):
    """Output handler that saves Solid Preference Index to the data repository database."""

    def __init__(self, session_id: str, unit_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the SolidPreferenceIndices table if it doesn't exist."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS SolidPreferenceIndices \
                           ( \
                               session_id             VARCHAR(10)  NOT NULL, \
                               unit_name              VARCHAR(255) NOT NULL, \
                               solid_preference_index FLOAT        NOT NULL, \
                               PRIMARY KEY (session_id, unit_name), \
                               CONSTRAINT SolidPreferenceIndices_ibfk_1 \
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                       ON DELETE CASCADE
                           ) CHARSET = latin1; \
                           """
        self.conn.execute(create_table_sql)

    def process(self, result: float) -> float:
        """Save the Solid Preference Index to the database."""
        # Get session ID from context

        # session_id, _ = read_session_id_from_db_name(context.ga_database)

        # Insert or update the record
        upsert_sql = """
                     INSERT INTO SolidPreferenceIndices (session_id, unit_name, solid_preference_index)
                     VALUES (%s, %s, %s)
                     ON DUPLICATE KEY UPDATE solid_preference_index = VALUES(solid_preference_index) \
                     """

        self.conn.execute(upsert_sql, (self.session_id, self.unit_name, result))
        print(f"Saved Solid Preference Index for session {self.session_id}, unit {self.unit_name}: {result}")

        return result
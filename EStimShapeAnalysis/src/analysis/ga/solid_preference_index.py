import numpy as np
import pandas as pd
from typing import Optional
from clat.util.connection import Connection
from clat.pipeline.pipeline_base_classes import ComputationModule, InputT, OutputT, AnalysisModuleFactory, OutputHandler
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context


def create_sp_index_module(channel=None, session_id=None, spike_data_col=None):
    index_module = AnalysisModuleFactory.create(
        computation=SolidPreferenceIndexCalculator(response_key=channel, spike_data_col=spike_data_col),
        output_handler=SolidPreferenceIndexDBSaver(session_id, channel)
    )
    return index_module


class SolidPreferenceIndexCalculator(ComputationModule):
    def __init__(self,*, response_key = None , spike_data_col = "Spike Rate by channel"):
        self.response_key = response_key
        self.spike_data_col = spike_data_col

    def compute(self, prepared_data: InputT) -> OutputT:
        # Filter for 3D and 2D test types
        data_3d = prepared_data[prepared_data['TestType'] == '3D']
        data_2d = prepared_data[prepared_data['TestType'] == '2D']

        # Extract spike rates for this channel to determine top half
        def get_spike_rates_for_channel(data, channel_key):
            spike_rates = []
            for _, row in data.iterrows():
                spike_rate_dict = row[self.spike_data_col]
                if isinstance(spike_rate_dict, dict) and channel_key in spike_rate_dict:
                    spike_rates.append(spike_rate_dict[channel_key])
            return spike_rates

        # Get spike rates for 3D data
        spike_rates_3d = get_spike_rates_for_channel(data_3d, self.response_key)
        if spike_rates_3d:
            median_3d = np.median(spike_rates_3d)
            # Filter to top half (above median)
            data_3d_filtered = []
            for _, row in data_3d.iterrows():
                spike_rate_dict = row[self.spike_data_col]
                if isinstance(spike_rate_dict, dict) and self.response_key in spike_rate_dict:
                    if spike_rate_dict[self.response_key] >= median_3d:
                        data_3d_filtered.append(row)
            data_3d = pd.DataFrame(data_3d_filtered) if data_3d_filtered else pd.DataFrame()

        # Get spike rates for 2D data
        spike_rates_2d = get_spike_rates_for_channel(data_2d, self.response_key)
        if spike_rates_2d:
            median_2d = np.median(spike_rates_2d)
            # Filter to top half (above median)
            data_2d_filtered = []
            for _, row in data_2d.iterrows():
                spike_rate_dict = row[self.spike_data_col]
                if isinstance(spike_rate_dict, dict) and self.response_key in spike_rate_dict:
                    if spike_rate_dict[self.response_key] >= median_2d:
                        data_2d_filtered.append(row)
            data_2d = pd.DataFrame(data_2d_filtered) if data_2d_filtered else pd.DataFrame()

        # Analyze only the specific channel on filtered data
        total_3d_rate = 0
        for _, row in data_3d.iterrows():
            spike_rates = row[self.spike_data_col]
            if isinstance(spike_rates, dict) and self.response_key in spike_rates:
                total_3d_rate += spike_rates[self.response_key]

        total_2d_rate = 0
        for _, row in data_2d.iterrows():
            spike_rates = row[self.spike_data_col]
            if isinstance(spike_rates, dict) and self.response_key in spike_rates:
                total_2d_rate += spike_rates[self.response_key]

        solid_preference_index = (total_3d_rate - total_2d_rate) / max(total_3d_rate, total_2d_rate)

        print(f"3D data: {len(data_3d)} trials (top half), total rate: {total_3d_rate}")
        print(f"2D data: {len(data_2d)} trials (top half), total rate: {total_2d_rate}")
        print(f"The Solid Preference Index of {self.response_key} is: {solid_preference_index}")

        return solid_preference_index

class SolidPreferenceIndexDBSaver(OutputHandler):
    """Output handler that saves Solid Preference Index to the data repository database."""

    def __init__(self, session_id: str, unit_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()
        # self._clear_session_data()

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

    def _clear_session_data(self):
        """Delete all existing entries for this session."""
        delete_sql = "DELETE FROM SolidPreferenceIndices WHERE session_id = %s"
        self.conn.execute(delete_sql, (self.session_id,))
        print(f"Cleared existing Solid Preference Index data for session {self.session_id}")

    def process(self, result: float) -> float:
        """Save the Solid Preference Index to the database."""
        # Insert or update if the key already exists
        insert_sql = """
                     INSERT INTO SolidPreferenceIndices (session_id, unit_name, solid_preference_index)
                     VALUES (%s, %s, %s)
                     ON DUPLICATE KEY UPDATE solid_preference_index = VALUES(solid_preference_index)
                     """

        self.conn.execute(insert_sql, (self.session_id, self.unit_name, result))
        print(f"Saved Solid Preference Index for session {self.session_id}, unit {self.unit_name}: {result}")

        return result
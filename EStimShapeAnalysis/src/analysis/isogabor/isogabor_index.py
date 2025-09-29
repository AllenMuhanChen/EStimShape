import numpy as np

from clat.pipeline.pipeline_base_classes import ComputationModule, InputT, OutputT

from clat.util.connection import Connection
from clat.pipeline.pipeline_base_classes import OutputHandler
from src.repository.export_to_repository import read_session_id_from_db_name

from clat.pipeline.pipeline_base_classes import AnalysisModuleFactory


def create_isochromatic_index_module(channel=None, session_id=None, spike_data_col=None):
    index_module = AnalysisModuleFactory.create(
        computation=IsochromaticPreferenceIndexCalculator(response_key=channel, spike_data_col=spike_data_col),
        output_handler=IsochromaticPreferenceIndexDBSaver(session_id, channel)
    )
    return index_module


class IsochromaticPreferenceIndexDBSaver(OutputHandler):
    """Output handler that saves Isochromatic Preference Index to the data repository database."""

    def __init__(self, session_id: str, unit_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()
        self._clear_session_data()

    def _ensure_table_exists(self):
        """Create the IsochromaticPreferenceIndices table if it doesn't exist."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS IsochromaticPreferenceIndices \
                           ( \
                               session_id                    VARCHAR(10)  NOT NULL, \
                               unit_name                     VARCHAR(255) NOT NULL, \
                               frequency                     FLOAT        NOT NULL, \
                               isochromatic_preference_index FLOAT        NOT NULL, \
                               PRIMARY KEY (session_id, unit_name, frequency), \
                               CONSTRAINT IsochromaticPreferenceIndices_ibfk_1 \
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                       ON DELETE CASCADE
                           ) CHARSET = latin1; \
                           """
        self.conn.execute(create_table_sql)

    def _clear_session_data(self):
        """Delete all existing entries for this session and unit."""
        delete_sql = "DELETE FROM IsochromaticPreferenceIndices WHERE session_id = %s AND unit_name = %s"
        self.conn.execute(delete_sql, (self.session_id, self.unit_name))
        print(
            f"Cleared existing Isochromatic Preference Index data for session {self.session_id}, unit {self.unit_name}")

    def process(self, result: dict) -> dict:
        """Save the Isochromatic Preference Index for each frequency to the database."""
        # result is now a dictionary mapping frequencies to indices
        for frequency, index_value in result.items():
            if not np.isnan(frequency):
                insert_sql = """
                             INSERT INTO IsochromaticPreferenceIndices (session_id, unit_name, frequency, isochromatic_preference_index)
                             VALUES (%s, %s, %s, %s)
                             """

                self.conn.execute(insert_sql, (self.session_id, self.unit_name, float(frequency), float(index_value)))
                print(
                    f"Saved Isochromatic Preference Index for session {self.session_id}, unit {self.unit_name}, frequency {frequency}: {index_value}")

        return result


class IsochromaticPreferenceIndexCalculator(ComputationModule):
    def __init__(self, *, response_key: str = None, spike_data_col: str = None):
        self.response_key = response_key
        self.spike_data_col = spike_data_col

    def compute(self, prepared_data: InputT) -> OutputT:
        def get_sum_for_type_and_frequency(data, type_name, frequency):
            """Helper function to sum spike rates for a specific type and frequency."""
            type_frequency_data = data[(data['Type'] == type_name) & (data['Frequency'] == frequency)]
            total_rate = 0
            for _, row in type_frequency_data.iterrows():
                spike_rates = row[self.spike_data_col]
                if isinstance(spike_rates, dict) and self.response_key in spike_rates:
                    total_rate += spike_rates[self.response_key]
            return total_rate

        # Get unique frequencies
        frequencies = sorted(prepared_data['Frequency'].unique())
        print(f"Calculating isochromatic preference indices for frequencies: {frequencies}")

        frequency_indices = {}

        for frequency in frequencies:
            print(f"\nProcessing frequency: {frequency}")

            # Get sums for individual colors (isochromatic) at this frequency
            red_sum = get_sum_for_type_and_frequency(prepared_data, 'Red', frequency)
            green_sum = get_sum_for_type_and_frequency(prepared_data, 'Green', frequency)
            cyan_sum = get_sum_for_type_and_frequency(prepared_data, 'Cyan', frequency)
            orange_sum = get_sum_for_type_and_frequency(prepared_data, 'Orange', frequency)

            # Get sums for mixed colors (isoluminant) at this frequency
            red_green_sum = get_sum_for_type_and_frequency(prepared_data, 'RedGreen', frequency)
            cyan_orange_sum = get_sum_for_type_and_frequency(prepared_data, 'CyanOrange', frequency)

            # Find max isochromatic sum
            max_isochromatic_sum = max(red_sum, green_sum, cyan_sum, orange_sum)

            # Find max isoluminant sum
            max_isoluminant_sum = max(red_green_sum, cyan_orange_sum)

            # Calculate the metric: (max isochromatic - max isoluminant) / max(mics, mils)
            if max_isochromatic_sum == 0 and max_isoluminant_sum == 0:
                isochromatic_preference_index = 0.0
                print(f"  Warning: No data for frequency {frequency}, setting index to 0")
            else:
                isochromatic_preference_index = (max_isochromatic_sum - max_isoluminant_sum) / max(max_isochromatic_sum,
                                                                                                   max_isoluminant_sum)

            frequency_indices[frequency] = isochromatic_preference_index

            print(
                f"  Individual color sums - Red: {red_sum}, Green: {green_sum}, Cyan: {cyan_sum}, Orange: {orange_sum}")
            print(f"  Mixed color sums - RedGreen: {red_green_sum}, CyanOrange: {cyan_orange_sum}")
            print(f"  Max isochromatic sum: {max_isochromatic_sum}")
            print(f"  Max isoluminant sum: {max_isoluminant_sum}")
            print(
                f"  Isochromatic Preference Index for {self.response_key} at {frequency} Hz: {isochromatic_preference_index}")

        print(f"\nFinal frequency-specific indices for {self.response_key}: {frequency_indices}")
        return frequency_indices
from clat.pipeline.pipeline_base_classes import ComputationModule, InputT, OutputT

from clat.util.connection import Connection
from clat.pipeline.pipeline_base_classes import OutputHandler
from src.repository.export_to_repository import read_session_id_from_db_name
from src.startup import context

from clat.pipeline.pipeline_base_classes import AnalysisModuleFactory

def create_isochromatic_index_module(channel=None, session_id=None):
    index_module = AnalysisModuleFactory.create(
        computation=IsochromaticPreferenceIndexCalculator(channel),
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

    def _ensure_table_exists(self):
        """Create the IsochromaticPreferenceIndices table if it doesn't exist."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS IsochromaticPreferenceIndices \
                           ( \
                               session_id                    VARCHAR(10)  NOT NULL, \
                               unit_name                     VARCHAR(255) NOT NULL, \
                               isochromatic_preference_index FLOAT        NOT NULL, \
                               PRIMARY KEY (session_id, unit_name), \
                               CONSTRAINT IsochromaticPreferenceIndices_ibfk_1 \
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                       ON DELETE CASCADE
                           ) CHARSET = latin1; \
                           """
        self.conn.execute(create_table_sql)

    def process(self, result: float) -> float:
        """Save the Isochromatic Preference Index to the database."""
        # Get session ID from context
        # session_id, _ = read_session_id_from_db_name(context.isogabor_database)

        # Insert or update the record
        upsert_sql = """
                     INSERT INTO IsochromaticPreferenceIndices (session_id, unit_name, isochromatic_preference_index)
                     VALUES (%s, %s, %s)
                     ON DUPLICATE KEY UPDATE isochromatic_preference_index = VALUES(isochromatic_preference_index) \
                     """

        self.conn.execute(upsert_sql, (self.session_id, self.unit_name, result))
        print(f"Saved Isochromatic Preference Index for session {self.session_id}, unit {self.unit_name}: {result}")

        return result


class IsochromaticPreferenceIndexCalculator(ComputationModule):
    def __init__(self, response_key: str):
        self.response_key = response_key

    def compute(self, prepared_data: InputT) -> OutputT:
        def get_sum_for_type(data, type_name):
            """Helper function to sum spike rates for a specific type."""
            type_data = data[data['Type'] == type_name]
            total_rate = 0
            for _, row in type_data.iterrows():
                spike_rates = row['Spike Rate by channel']
                if isinstance(spike_rates, dict) and self.response_key in spike_rates:
                    total_rate += spike_rates[self.response_key]
            return total_rate

        # Get sums for individual colors (isochromatic)
        red_sum = get_sum_for_type(prepared_data, 'Red')
        green_sum = get_sum_for_type(prepared_data, 'Green')
        cyan_sum = get_sum_for_type(prepared_data, 'Cyan')
        orange_sum = get_sum_for_type(prepared_data, 'Orange')

        # Get sums for mixed colors (isoluminant)
        red_green_sum = get_sum_for_type(prepared_data, 'RedGreen')
        cyan_orange_sum = get_sum_for_type(prepared_data, 'CyanOrange')

        # Find max isochromatic sum
        max_isochromatic_sum = max(red_sum, green_sum, cyan_sum, orange_sum)

        # Find max isoluminant sum
        max_isoluminant_sum = max(red_green_sum, cyan_orange_sum)

        # Calculate the metric: (max isochromatic - max isoluminant) / max(mics, mils)
        isochromatic_preference_index = (max_isochromatic_sum - max_isoluminant_sum) / max(max_isochromatic_sum,
                                                                                           max_isoluminant_sum)

        print(f"Individual color sums - Red: {red_sum}, Green: {green_sum}, Cyan: {cyan_sum}, Orange: {orange_sum}")
        print(f"Mixed color sums - RedGreen: {red_green_sum}, CyanOrange: {cyan_orange_sum}")
        print(f"Max isochromatic sum: {max_isochromatic_sum}")
        print(f"Max isoluminant sum: {max_isoluminant_sum}")
        print(f"Final Isochromatic Preference Index for {self.response_key}: {isochromatic_preference_index}")

        return isochromatic_preference_index
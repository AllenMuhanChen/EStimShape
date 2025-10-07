import numpy as np
import pandas as pd
import json
from clat.pipeline.pipeline_base_classes import ComputationModule, AnalysisModuleFactory, OutputHandler
from clat.util.connection import Connection


class PreferredFrequencyCalculator(ComputationModule):
    """Calculate the preferred frequency for a unit based on maximum responses."""

    def __init__(self, *, response_key=None, spike_data_col="Spike Rate by channel",
                 type_col='Type', frequency_col='Frequency', filter_values=None):
        self.response_key = response_key
        self.spike_data_col = spike_data_col
        self.type_col = type_col
        self.frequency_col = frequency_col
        self.filter_values = filter_values or {}

    def compute(self, prepared_data):
        """
        Calculate preferred frequency by finding the frequency with the highest maximum response.

        Algorithm:
        1. For each frequency, find the maximum response across all types
        2. The preferred frequency is the one with the highest maximum
        3. Save all frequencies with their max responses

        Returns:
            Dictionary with preferred frequency and related statistics
        """
        # Filter data if specified
        data = prepared_data.copy()
        for col, values in self.filter_values.items():
            if col in data.columns:
                data = data[data[col].isin(values)]

        # Extract spike rates for this channel
        spike_rates = []
        types = []
        frequencies = []

        for _, row in data.iterrows():
            spike_rate_dict = row[self.spike_data_col]
            if isinstance(spike_rate_dict, dict) and self.response_key in spike_rate_dict:
                spike_rates.append(spike_rate_dict[self.response_key])
                types.append(row[self.type_col])
                frequencies.append(row[self.frequency_col])

        # Create DataFrame
        df = pd.DataFrame({
            'Type': types,
            'Frequency': frequencies,
            'SpikeRate': spike_rates
        })

        if df.empty:
            print(f"No data found for channel {self.response_key}")
            return None

        # Calculate average spike rate for each Type-Frequency combination
        grouped = df.groupby([self.type_col, self.frequency_col])['SpikeRate'].mean().reset_index()

        # For each frequency, find the maximum response across all types
        max_by_freq = grouped.groupby(self.frequency_col)['SpikeRate'].max().reset_index()
        max_by_freq.columns = ['Frequency', 'MaxResponse']

        # Create dictionary of all frequencies and their max responses
        all_freq_responses = {float(row['Frequency']): float(row['MaxResponse'])
                              for _, row in max_by_freq.iterrows()}

        # Find the frequency with the highest maximum
        preferred_idx = max_by_freq['MaxResponse'].idxmax()
        preferred_frequency = max_by_freq.loc[preferred_idx, 'Frequency']
        max_response = max_by_freq.loc[preferred_idx, 'MaxResponse']

        # Find which type(s) had the maximum response at the preferred frequency
        preferred_freq_data = grouped[grouped[self.frequency_col] == preferred_frequency]
        best_type = preferred_freq_data.loc[preferred_freq_data['SpikeRate'].idxmax(), 'Type']

        # Calculate overall average response for comparison
        overall_avg = df['SpikeRate'].mean()

        print(f"\nPreferred Frequency Analysis for {self.response_key}:")
        print(f"  Preferred frequency: {preferred_frequency}")
        print(f"  Maximum response: {max_response:.2f} spikes/s")
        print(f"  Best stimulus type at preferred freq: {best_type}")
        print(f"  Overall average response: {overall_avg:.2f} spikes/s")
        print(f"  All frequency max responses: {all_freq_responses}")

        return {
            'channel': self.response_key,
            'preferred_frequency': preferred_frequency,
            'max_response': max_response,
            'best_type': best_type,
            'overall_avg_response': overall_avg,
            'all_freq_responses': all_freq_responses,
            'max_by_freq': max_by_freq
        }


class PreferredFrequencyDBSaver(OutputHandler):
    """Save preferred frequency to database."""

    def __init__(self, session_id: str, unit_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the PreferredFrequencies table if it doesn't exist."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS PreferredFrequencies
                           (
                               session_id           VARCHAR(10)  NOT NULL,
                               unit_name            VARCHAR(255) NOT NULL,
                               preferred_frequency  FLOAT        NOT NULL,
                               max_response         FLOAT        NOT NULL,
                               best_type            VARCHAR(50)  NOT NULL,
                               overall_avg_response FLOAT        NOT NULL,
                               all_freq_responses   TEXT         NULL,
                               PRIMARY KEY (session_id, unit_name),
                               CONSTRAINT PreferredFrequencies_ibfk_1
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id)
                                       ON DELETE CASCADE
                           ) CHARSET = latin1;
                           """
        self.conn.execute(create_table_sql)

    def process(self, result: dict) -> dict:
        """Save the preferred frequency to the database."""
        if result is None:
            print(f"No results to save for {self.unit_name}")
            return None

        try:
            # Convert all_freq_responses dict to JSON string
            all_freq_json = json.dumps(result['all_freq_responses'])

            insert_sql = """
                         INSERT INTO PreferredFrequencies
                         (session_id, unit_name, preferred_frequency, max_response, best_type,
                          overall_avg_response, all_freq_responses)
                         VALUES (%s, %s, %s, %s, %s, %s, %s)
                         ON DUPLICATE KEY UPDATE preferred_frequency  = VALUES(preferred_frequency),
                                                 max_response         = VALUES(max_response),
                                                 best_type            = VALUES(best_type),
                                                 overall_avg_response = VALUES(overall_avg_response),
                                                 all_freq_responses   = VALUES(all_freq_responses)
                         """

            self.conn.execute(insert_sql, (
                self.session_id,
                self.unit_name,
                float(result['preferred_frequency']),
                float(result['max_response']),
                str(result['best_type']),
                float(result['overall_avg_response']),
                all_freq_json
            ))

            print(f"\nSaved preferred frequency for session {self.session_id}, unit {self.unit_name}")
            print(f"  Frequency: {result['preferred_frequency']}, Max response: {result['max_response']:.2f}")

        except Exception as e:
            print(f"Could not save to database (session may not be initialized): {e}")
            print(f"\nPreferred Frequency Results:")
            print(f"Session: {self.session_id}, Unit: {self.unit_name}")
            print(f"  Preferred frequency: {result['preferred_frequency']}")
            print(f"  Max response: {result['max_response']:.2f}")
            print(f"  Best type: {result['best_type']}")
            print(f"  All frequencies: {result['all_freq_responses']}")

        return result


def create_preferred_frequency_module(channel=None, session_id=None, spike_data_col=None,
                                      filter_values=None):
    """
    Create a module for calculating preferred frequency.

    Args:
        channel: Channel/unit to analyze
        session_id: Session identifier
        spike_data_col: Column containing spike rate data
        filter_values: Dictionary of column:values to filter data
    """
    pref_freq_module = AnalysisModuleFactory.create(
        computation=PreferredFrequencyCalculator(
            response_key=channel,
            spike_data_col=spike_data_col,
            filter_values=filter_values
        ),
        output_handler=PreferredFrequencyDBSaver(session_id, channel)
    )
    return pref_freq_module
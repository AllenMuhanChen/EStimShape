import numpy as np
import pandas as pd

from clat.pipeline.pipeline_base_classes import AnalysisModuleFactory
from clat.pipeline.pipeline_base_classes import ComputationModule, InputT, OutputT
from clat.pipeline.pipeline_base_classes import OutputHandler
from clat.pipeline.pipeline_base_classes import create_pipeline, create_branch
from clat.util.connection import Connection
from src.analysis import Analysis
from src.repository.import_from_repository import import_from_repository


def create_isoluminant_comparison_module(channel=None, session_id=None, spike_data_col=None,
                                         metric_name='max_normalized'):
    """
    Create a module for calculating isoluminant comparison scores.

    Args:
        channel: Channel/unit name to analyze
        session_id: Session identifier
        spike_data_col: Column name containing spike rate data
        metric_name: Type of metric to calculate (default: 'max_normalized')

    Returns:
        AnalysisModule configured for isoluminant comparison
    """
    comparison_module = AnalysisModuleFactory.create(
        computation=IsoluminantComparisonCalculator(
            response_key=channel,
            spike_data_col=spike_data_col,
            metric_name=metric_name
        ),
        output_handler=IsoluminantComparisonDBSaver(session_id, channel, metric_name)
    )
    return comparison_module


class IsoluminantComparisonDBSaver(OutputHandler):
    """Output handler that saves isoluminant comparison data to the database."""

    def __init__(self, session_id: str, unit_name: str, metric_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.metric_name = metric_name
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()
        self._clear_session_data()

    def _ensure_table_exists(self):
        """Create the IsoluminantComparisons table if it doesn't exist."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS IsoluminantComparisons \
                           ( \
                               session_id  VARCHAR(10)  NOT NULL, \
                               unit        VARCHAR(255) NOT NULL, \
                               frequency   FLOAT        NOT NULL, \
                               red_green   FLOAT        NOT NULL, \
                               cyan_orange FLOAT        NOT NULL, \
                               metric_name VARCHAR(255) NOT NULL, \
                               PRIMARY KEY (session_id, unit, frequency, metric_name), \
                               CONSTRAINT IsoluminantComparisons_ibfk_1 \
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                       ON DELETE CASCADE
                           ) CHARSET = latin1; \
                           """
        self.conn.execute(create_table_sql)

    def _clear_session_data(self):
        """Delete all existing entries for this session, unit, and metric."""
        delete_sql = """
                     DELETE \
                     FROM IsoluminantComparisons
                     WHERE session_id = %s \
                       AND unit = %s \
                       AND metric_name = %s \
                     """
        self.conn.execute(delete_sql, (self.session_id, self.unit_name, self.metric_name))
        print(f"Cleared existing isoluminant comparison data for session {self.session_id}, "
              f"unit {self.unit_name}, metric {self.metric_name}")

    def process(self, result: dict) -> dict:
        """
        Save the isoluminant comparison scores to the database.

        Args:
            result: Dictionary with structure {frequency: {'red_green': value, 'cyan_orange': value}}
        """
        for frequency, scores in result.items():
            if not np.isnan(frequency):
                insert_sql = """
                             INSERT INTO IsoluminantComparisons
                                 (session_id, unit, frequency, red_green, cyan_orange, metric_name)
                             VALUES (%s, %s, %s, %s, %s, %s) \
                             """

                self.conn.execute(insert_sql, (
                    self.session_id,
                    self.unit_name,
                    float(frequency),
                    float(scores['red_green']),
                    float(scores['cyan_orange']),
                    self.metric_name
                ))
                print(f"Saved isoluminant comparison for session {self.session_id}, "
                      f"unit {self.unit_name}, frequency {frequency}: "
                      f"RG={scores['red_green']:.4f}, CO={scores['cyan_orange']:.4f}")

        return result


class IsoluminantComparisonCalculator(ComputationModule):
    """
    Calculate isoluminant comparison scores for RedGreen vs CyanOrange stimuli.

    For max_normalized metric:
    1. Find global maximum response across all stimulus types and frequencies
    2. Calculate mean response for RedGreen and CyanOrange at each frequency
    3. Normalize each by the global maximum
    """

    def __init__(self, *, response_key: str = None, spike_data_col: str = None, metric_name: str = 'max_normalized'):
        self.response_key = response_key
        self.spike_data_col = spike_data_col
        self.metric_name = metric_name

    def compute(self, prepared_data: InputT) -> OutputT:
        """
        Compute isoluminant comparison scores.

        Args:
            prepared_data: DataFrame with columns including 'Type', 'Frequency', and spike_data_col

        Returns:
            Dictionary mapping frequencies to {red_green, cyan_orange} scores
        """

        def get_mean_for_type_and_frequency(data, type_name, frequency):
            """Helper function to calculate mean spike rate for a specific type and frequency."""
            type_frequency_data = data[(data['Type'] == type_name) & (data['Frequency'] == frequency)]

            if len(type_frequency_data) == 0:
                return 0.0

            rates = []
            for _, row in type_frequency_data.iterrows():
                spike_rates = row[self.spike_data_col]
                if isinstance(spike_rates, dict) and self.response_key in spike_rates:
                    rates.append(spike_rates[self.response_key])

            return np.mean(rates) if rates else 0.0

        # Get unique frequencies
        frequencies = sorted(prepared_data['Frequency'].unique())
        print(f"Calculating isoluminant comparison scores for frequencies: {frequencies}")

        if self.metric_name == 'max_normalized':
            # Calculate global maximum across all types and frequencies
            all_types = ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
            global_max = 0.0

            for freq in frequencies:
                for stim_type in all_types:
                    mean_response = get_mean_for_type_and_frequency(prepared_data, stim_type, freq)
                    global_max = max(global_max, mean_response)

            print(f"Global maximum response across all conditions: {global_max:.4f}")

            if global_max == 0:
                print("Warning: Global maximum is 0, setting all normalized values to 0")
                frequency_scores = {}
                for frequency in frequencies:
                    frequency_scores[frequency] = {
                        'red_green': 0.0,
                        'cyan_orange': 0.0
                    }
                return frequency_scores
        else:
            raise ValueError(f"Unknown metric_name: {self.metric_name}")

        # Calculate scores for each frequency
        frequency_scores = {}

        for frequency in frequencies:
            print(f"\nProcessing frequency: {frequency}")

            # Get mean responses for isoluminant stimuli
            red_green_mean = get_mean_for_type_and_frequency(prepared_data, 'RedGreen', frequency)
            cyan_orange_mean = get_mean_for_type_and_frequency(prepared_data, 'CyanOrange', frequency)

            # Normalize by global maximum
            red_green_normalized = red_green_mean / global_max if global_max > 0 else 0.0
            cyan_orange_normalized = cyan_orange_mean / global_max if global_max > 0 else 0.0

            frequency_scores[frequency] = {
                'red_green': red_green_normalized,
                'cyan_orange': cyan_orange_normalized
            }

            print(f"  RedGreen mean: {red_green_mean:.4f}, normalized: {red_green_normalized:.4f}")
            print(f"  CyanOrange mean: {cyan_orange_mean:.4f}, normalized: {cyan_orange_normalized:.4f}")

        print(f"\nFinal isoluminant comparison scores for {self.response_key}:")
        for freq, scores in frequency_scores.items():
            print(f"  {freq} Hz: RG={scores['red_green']:.4f}, CO={scores['cyan_orange']:.4f}")

        return frequency_scores


class IsoluminantComparisonAnalysis(Analysis):
    """Analysis class for calculating isoluminant comparison scores."""

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        """
        Run isoluminant comparison analysis for a single channel.

        Args:
            channel: Channel/unit name to analyze
            compiled_data: Optional pre-compiled data. If None, will import from repository.

        Returns:
            Dictionary with comparison scores for each frequency
        """
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'isogabor',
                'IsoGaborStimInfo',
                self.response_table,
            )

        # Create the comparison module
        comparison_module = create_isoluminant_comparison_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='max_normalized'
        )

        # Create pipeline
        comparison_branch = create_branch().then(comparison_module)
        pipeline = create_pipeline().make_branch(comparison_branch).build()

        # Run the pipeline
        result = pipeline.run(compiled_data)
        return result

    def compile_and_export(self):
        """Not implemented for this analysis."""
        raise NotImplementedError("compile_and_export not implemented for IsoluminantComparisonAnalysis")

    def compile(self):
        """Not implemented for this analysis."""
        raise NotImplementedError("compile not implemented for IsoluminantComparisonAnalysis")
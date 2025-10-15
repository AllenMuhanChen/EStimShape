import numpy as np
import pandas as pd

from clat.pipeline.pipeline_base_classes import AnalysisModuleFactory
from clat.pipeline.pipeline_base_classes import ComputationModule, InputT, OutputT
from clat.pipeline.pipeline_base_classes import OutputHandler
from clat.util.connection import Connection
from src.analysis import Analysis
from clat.pipeline.pipeline_base_classes import create_pipeline, create_branch
from src.analysis.isogabor.isogabor_raster_pipeline import IsochromaticIndexAnalysis
from src.repository.import_from_repository import import_from_repository


class IsoChromaticLuminantScoreAnalysis(IsochromaticIndexAnalysis):
    """Analysis class for calculating IsoChromaticLuminantScores."""

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                'isogabor',
                'IsoGaborStimInfo',
                self.response_table,
            )

        # Create the score module
        score_module = create_isochromatic_luminant_score_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='raw_spikes_per_second'
        )

        # Create pipeline
        score_branch = create_branch().then(score_module)
        pipeline = create_pipeline().make_branch(score_branch).build()

        # Run the pipeline
        result = pipeline.run(compiled_data)
        return result

def create_isochromatic_luminant_score_module(channel=None, session_id=None, spike_data_col=None, metric_name='raw_spikes_per_second'):
    """Factory function to create the IsoChromaticLuminantScore analysis module."""
    score_module = AnalysisModuleFactory.create(
        computation=IsoChromaticLuminantScoreCalculator(
            response_key=channel,
            spike_data_col=spike_data_col,
            metric_name=metric_name
        ),
        output_handler=IsoChromaticLuminantScoreDBSaver(session_id, channel, metric_name)
    )
    return score_module


class IsoChromaticLuminantScoreDBSaver(OutputHandler):
    """Output handler that saves IsoChromaticLuminantScore to the data repository database."""

    def __init__(self, session_id: str, unit_name: str, metric_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.metric_name = metric_name
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the IsoChromaticLuminantScores table if it doesn't exist."""
        try:
            create_table_sql = """
                               CREATE TABLE IF NOT EXISTS IsoChromaticLuminantScores \
                               ( \
                                   session_id         VARCHAR(10)  NOT NULL, \
                                   unit_name          VARCHAR(255) NOT NULL, \
                                   frequency          FLOAT        NOT NULL, \
                                   metric_name        VARCHAR(255) NOT NULL, \
                                   isochromatic_score FLOAT        NOT NULL, \
                                   isoluminant_score  FLOAT        NOT NULL, \
                                   PRIMARY KEY (session_id, unit_name, frequency, metric_name), \
                                   CONSTRAINT IsoChromaticLuminantScores_ibfk_1 \
                                       FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                           ON DELETE CASCADE
                               ) CHARSET = latin1;
                               """
            self.conn.execute(create_table_sql)
            self._clear_session_data()
        except Exception as e:
            print(f"Warning: Could not initialize database: {e}")
            print("Will print results instead of saving to database.")

    def _clear_session_data(self):
        """Delete all existing entries for this session, unit, and metric."""
        delete_sql = "DELETE FROM IsoChromaticLuminantScores WHERE session_id = %s AND unit_name = %s AND metric_name = %s"
        self.conn.execute(delete_sql, (self.session_id, self.unit_name, self.metric_name))
        print(
            f"Cleared existing IsoChromaticLuminantScore data for session {self.session_id}, unit {self.unit_name}, metric {self.metric_name}")

    def process(self, result: dict) -> dict:
        """Save the scores for each frequency to the database, or print if database unavailable."""
        for frequency, (isochromatic_score, isoluminant_score) in result.items():
            if not np.isnan(frequency):
                try:
                    insert_sql = """
                                 INSERT INTO IsoChromaticLuminantScores
                                 (session_id, unit_name, frequency, metric_name, isochromatic_score, isoluminant_score)
                                 VALUES (%s, %s, %s, %s, %s, %s)
                                 """

                    self.conn.execute(insert_sql, (
                        self.session_id,
                        self.unit_name,
                        float(frequency),
                        self.metric_name,
                        float(isochromatic_score),
                        float(isoluminant_score)
                    ))
                    print(f"Saved IsoChromaticLuminantScore for session {self.session_id}, unit {self.unit_name}, "
                          f"frequency {frequency}, metric {self.metric_name}: "
                          f"isochromatic={isochromatic_score}, isoluminant={isoluminant_score}")
                except Exception as e:
                    print(f"Warning: Could not save to database: {e}")
                    print(f"Results - session {self.session_id}, unit {self.unit_name}, "
                          f"frequency {frequency}, metric {self.metric_name}: "
                          f"isochromatic={isochromatic_score}, isoluminant={isoluminant_score}")

        return result


class IsoChromaticLuminantScoreCalculator(ComputationModule):
    """Computes isochromatic and isoluminant scores for each frequency."""

    def __init__(self, *, response_key: str = None, spike_data_col: str = None,
                 metric_name: str = 'raw_spikes_per_second'):
        self.response_key = response_key
        self.spike_data_col = spike_data_col
        self.metric_name = metric_name

    def compute(self, prepared_data: InputT) -> OutputT:
        """
        Calculate isochromatic and isoluminant scores for each frequency.
        Returns a dict mapping frequency -> (isochromatic_score, isoluminant_score)
        """

        def get_average_for_type_and_frequency(data, type_name, frequency):
            """Helper function to calculate average spike rate for a specific type and frequency."""
            type_frequency_data = data[(data['Type'] == type_name) & (data['Frequency'] == frequency)]

            if len(type_frequency_data) == 0:
                return 0.0

            rates = []
            for _, row in type_frequency_data.iterrows():
                spike_rates = row[self.spike_data_col]
                if isinstance(spike_rates, dict) and self.response_key in spike_rates:
                    rates.append(spike_rates[self.response_key])

            return np.mean(rates) if len(rates) > 0 else 0.0

        # Get unique frequencies
        frequencies = sorted(prepared_data['Frequency'].unique())
        print(f"Calculating IsoChromaticLuminantScores for frequencies: {frequencies}")

        frequency_scores = {}

        for frequency in frequencies:
            print(f"\nProcessing frequency: {frequency}")

            # Get averages for individual colors (isochromatic) at this frequency
            red_avg = get_average_for_type_and_frequency(prepared_data, 'Red', frequency)
            green_avg = get_average_for_type_and_frequency(prepared_data, 'Green', frequency)
            cyan_avg = get_average_for_type_and_frequency(prepared_data, 'Cyan', frequency)
            orange_avg = get_average_for_type_and_frequency(prepared_data, 'Orange', frequency)

            # Get averages for mixed colors (isoluminant) at this frequency
            red_green_avg = get_average_for_type_and_frequency(prepared_data, 'RedGreen', frequency)
            cyan_orange_avg = get_average_for_type_and_frequency(prepared_data, 'CyanOrange', frequency)

            # Find max isochromatic score
            isochromatic_score = max(red_avg, green_avg, cyan_avg, orange_avg)

            # Find max isoluminant score
            isoluminant_score = max(red_green_avg, cyan_orange_avg)

            frequency_scores[frequency] = (isochromatic_score, isoluminant_score)

            print(
                f"  Individual color averages - Red: {red_avg}, Green: {green_avg}, Cyan: {cyan_avg}, Orange: {orange_avg}")
            print(f"  Mixed color averages - RedGreen: {red_green_avg}, CyanOrange: {cyan_orange_avg}")
            print(f"  Isochromatic score: {isochromatic_score}")
            print(f"  Isoluminant score: {isoluminant_score}")

        print(
            f"\nFinal frequency-specific scores for {self.response_key}, metric {self.metric_name}: {frequency_scores}")
        return frequency_scores
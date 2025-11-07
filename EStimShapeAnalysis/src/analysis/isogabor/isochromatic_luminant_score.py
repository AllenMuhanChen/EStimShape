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

        # Create the score modules
        spike_score_module = create_isochromatic_luminant_score_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='raw_spikes_per_second'
        )

        z_score_module = create_isochromatic_luminant_score_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='z_score'
        )

        z_score_all_module = create_isochromatic_luminant_score_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='z_score_all'
        )

        max_normalized_module = create_isochromatic_luminant_score_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='max_normalized'
        )

        variance_cv_module = create_isochromatic_luminant_score_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='variance_cv'
        )

        entropy_module = create_isochromatic_luminant_score_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='entropy'
        )

        mean_all_normalized_module = create_isochromatic_luminant_score_module(
            channel=channel,
            session_id=self.session_id,
            spike_data_col=self.spike_rates_col,
            metric_name='mean_all_normalized'
        )

        # Create pipeline
        spike_score_branch = create_branch().then(spike_score_module)
        z_score_branch = create_branch().then(z_score_module)
        z_score_all_branch = create_branch().then(z_score_all_module)
        max_normalized_branch = create_branch().then(max_normalized_module)
        variance_cv_branch = create_branch().then(variance_cv_module)
        entropy_branch = create_branch().then(entropy_module)
        mean_all_normalized_branch = create_branch().then(mean_all_normalized_module)

        pipeline = create_pipeline().make_branch(
            spike_score_branch,
            z_score_branch,
            z_score_all_branch,
            max_normalized_branch,
            variance_cv_branch,
            entropy_branch,
            mean_all_normalized_branch
        ).build()

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
            # For variance_cv metric, frequency will be None
            if frequency is None or not np.isnan(frequency):
                try:
                    insert_sql = """
                                 INSERT INTO IsoChromaticLuminantScores
                                 (session_id, unit_name, frequency, metric_name, isochromatic_score, isoluminant_score)
                                 VALUES (%s, %s, %s, %s, %s, %s)
                                 """

                    self.conn.execute(insert_sql, (
                        self.session_id,
                        self.unit_name,
                        float(frequency) if frequency is not None else 0,
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

        For variance_cv metric, returns {None: (isochromatic_cv, isoluminant_cv)}
        For entropy metric, returns {None: (isochromatic_entropy, isoluminant_entropy)}
        For mean_all_normalized metric, returns {None: (isochromatic_norm, isoluminant_norm)}
        For max_normalized metric, uses global max across all frequencies
        For z_score_all metric, uses global mean and std across all frequencies
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

        # For variance_cv, collect all means across frequencies
        if self.metric_name == 'variance_cv':
            isochromatic_cv, isoluminant_cv = self._calculate_variance_cv(
                frequencies, get_average_for_type_and_frequency, prepared_data
            )
            return {None: (isochromatic_cv, isoluminant_cv)}

        # For entropy, calculate Shannon's entropy
        if self.metric_name == 'entropy':
            isochromatic_entropy, isoluminant_entropy = self._calculate_entropy(
                frequencies, get_average_for_type_and_frequency, prepared_data
            )
            return {None: (isochromatic_entropy, isoluminant_entropy)}

        # For mean_all_normalized, normalize mean responses by max
        if self.metric_name == 'mean_all_normalized':
            isochromatic_norm, isoluminant_norm = self._calculate_mean_all_normalized(
                frequencies, get_average_for_type_and_frequency, prepared_data
            )
            return {None: (isochromatic_norm, isoluminant_norm)}

        # For max_normalized, first find global max across all frequencies and conditions
        if self.metric_name == 'max_normalized':
            all_responses = []
            for frequency in frequencies:
                red_avg = get_average_for_type_and_frequency(prepared_data, 'Red', frequency)
                green_avg = get_average_for_type_and_frequency(prepared_data, 'Green', frequency)
                cyan_avg = get_average_for_type_and_frequency(prepared_data, 'Cyan', frequency)
                orange_avg = get_average_for_type_and_frequency(prepared_data, 'Orange', frequency)
                red_green_avg = get_average_for_type_and_frequency(prepared_data, 'RedGreen', frequency)
                cyan_orange_avg = get_average_for_type_and_frequency(prepared_data, 'CyanOrange', frequency)
                all_responses.extend([red_avg, green_avg, cyan_avg, orange_avg, red_green_avg, cyan_orange_avg])

            global_max = max(all_responses) if all_responses else 1.0
            if global_max == 0:
                global_max = 1.0

            print(f"\nMax normalization: global max across all frequencies = {global_max:.2f}")

        # For z_score_all, first calculate global mean and std across all frequencies and conditions
        if self.metric_name == 'z_score_all':
            all_responses = []
            for frequency in frequencies:
                red_avg = get_average_for_type_and_frequency(prepared_data, 'Red', frequency)
                green_avg = get_average_for_type_and_frequency(prepared_data, 'Green', frequency)
                cyan_avg = get_average_for_type_and_frequency(prepared_data, 'Cyan', frequency)
                orange_avg = get_average_for_type_and_frequency(prepared_data, 'Orange', frequency)
                red_green_avg = get_average_for_type_and_frequency(prepared_data, 'RedGreen', frequency)
                cyan_orange_avg = get_average_for_type_and_frequency(prepared_data, 'CyanOrange', frequency)
                all_responses.extend([red_avg, green_avg, cyan_avg, orange_avg, red_green_avg, cyan_orange_avg])

            global_mean = np.mean(all_responses)
            global_std = np.std(all_responses, ddof=1) if len(all_responses) > 1 else 1.0

            if global_std == 0:
                global_std = 1.0

            print(
                f"\nZ-score (global) normalization: mean={global_mean:.2f}, std={global_std:.2f} across all frequencies")

        # Original logic for raw_spikes_per_second, z_score, z_score_all, and max_normalized metrics
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

            # Apply metric-specific transformations
            if self.metric_name == 'raw_spikes_per_second':
                # Use raw averages
                red_score = red_avg
                green_score = green_avg
                cyan_score = cyan_avg
                orange_score = orange_avg
                red_green_score = red_green_avg
                cyan_orange_score = cyan_orange_avg

            elif self.metric_name == 'z_score':
                # Calculate z-scores normalized within this frequency
                all_avgs = [red_avg, green_avg, cyan_avg, orange_avg, red_green_avg, cyan_orange_avg]
                mean_response = np.mean(all_avgs)
                std_response = np.std(all_avgs, ddof=1) if len(all_avgs) > 1 else 1.0

                # Avoid division by zero
                if std_response == 0:
                    std_response = 1.0

                # Z-score each average
                red_score = (red_avg - mean_response) / std_response
                green_score = (green_avg - mean_response) / std_response
                cyan_score = (cyan_avg - mean_response) / std_response
                orange_score = (orange_avg - mean_response) / std_response
                red_green_score = (red_green_avg - mean_response) / std_response
                cyan_orange_score = (cyan_orange_avg - mean_response) / std_response

                print(f"  Z-score normalization: mean={mean_response:.2f}, std={std_response:.2f}")

            elif self.metric_name == 'z_score_all':
                # Calculate z-scores using GLOBAL mean and std across all frequencies
                red_score = (red_avg - global_mean) / global_std
                green_score = (green_avg - global_mean) / global_std
                cyan_score = (cyan_avg - global_mean) / global_std
                orange_score = (orange_avg - global_mean) / global_std
                red_green_score = (red_green_avg - global_mean) / global_std
                cyan_orange_score = (cyan_orange_avg - global_mean) / global_std

            elif self.metric_name == 'max_normalized':
                # Normalize by GLOBAL max response across all frequencies
                red_score = red_avg / global_max
                green_score = green_avg / global_max
                cyan_score = cyan_avg / global_max
                orange_score = orange_avg / global_max
                red_green_score = red_green_avg / global_max
                cyan_orange_score = cyan_orange_avg / global_max

            else:
                raise ValueError(f"Unknown metric_name: {self.metric_name}")

            # Find max isochromatic score
            isochromatic_score = max(red_score, green_score, cyan_score, orange_score)

            # Find max isoluminant score
            isoluminant_score = max(red_green_score, cyan_orange_score)

            frequency_scores[frequency] = (isochromatic_score, isoluminant_score)

            print(f"  Individual color averages - Red: {red_avg:.2f}, Green: {green_avg:.2f}, "
                  f"Cyan: {cyan_avg:.2f}, Orange: {orange_avg:.2f}")
            print(f"  Mixed color averages - RedGreen: {red_green_avg:.2f}, CyanOrange: {cyan_orange_avg:.2f}")

            if self.metric_name == 'z_score':
                print(f"  Individual color z-scores - Red: {red_score:.2f}, Green: {green_score:.2f}, "
                      f"Cyan: {cyan_score:.2f}, Orange: {orange_score:.2f}")
                print(f"  Mixed color z-scores - RedGreen: {red_green_score:.2f}, CyanOrange: {cyan_orange_score:.2f}")
            elif self.metric_name == 'z_score_all':
                print(f"  Individual color z-scores (global) - Red: {red_score:.2f}, Green: {green_score:.2f}, "
                      f"Cyan: {cyan_score:.2f}, Orange: {orange_score:.2f}")
                print(
                    f"  Mixed color z-scores (global) - RedGreen: {red_green_score:.2f}, CyanOrange: {cyan_orange_score:.2f}")
            elif self.metric_name == 'max_normalized':
                print(f"  Individual color normalized - Red: {red_score:.3f}, Green: {green_score:.3f}, "
                      f"Cyan: {cyan_score:.3f}, Orange: {orange_score:.3f}")
                print(
                    f"  Mixed color normalized - RedGreen: {red_green_score:.3f}, CyanOrange: {cyan_orange_score:.3f}")

            print(f"  Isochromatic score: {isochromatic_score:.3f}")
            print(f"  Isoluminant score: {isoluminant_score:.3f}")

        print(
            f"\nFinal frequency-specific scores for {self.response_key}, metric {self.metric_name}: {frequency_scores}")
        return frequency_scores

    def _calculate_variance_cv(self, frequencies, get_average_for_type_and_frequency, prepared_data):
        """Calculate coefficient of variation for isochromatic and isoluminant responses."""
        isochromatic_means = []
        isoluminant_means = []

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

            # Collect means
            isochromatic_means.extend([red_avg, green_avg, cyan_avg, orange_avg])
            isoluminant_means.extend([red_green_avg, cyan_orange_avg])

            print(f"  Individual color averages - Red: {red_avg:.2f}, Green: {green_avg:.2f}, "
                  f"Cyan: {cyan_avg:.2f}, Orange: {orange_avg:.2f}")
            print(f"  Mixed color averages - RedGreen: {red_green_avg:.2f}, CyanOrange: {cyan_orange_avg:.2f}")

        # Calculate CV for isochromatic and isoluminant
        isochromatic_mean = np.mean(isochromatic_means)
        isochromatic_std = np.std(isochromatic_means, ddof=1)
        isochromatic_cv = isochromatic_std / isochromatic_mean if isochromatic_mean != 0 else 0.0

        isoluminant_mean = np.mean(isoluminant_means)
        isoluminant_std = np.std(isoluminant_means, ddof=1)
        isoluminant_cv = isoluminant_std / isoluminant_mean if isoluminant_mean != 0 else 0.0

        print(f"\nVariance CV calculation:")
        print(f"  Isochromatic - mean: {isochromatic_mean:.2f}, std: {isochromatic_std:.2f}, CV: {isochromatic_cv:.2f}")
        print(f"  Isoluminant - mean: {isoluminant_mean:.2f}, std: {isoluminant_std:.2f}, CV: {isoluminant_cv:.2f}")

        return isochromatic_cv, isoluminant_cv

    def _calculate_entropy(self, frequencies, get_average_for_type_and_frequency, prepared_data):
        """Calculate Shannon's entropy for isochromatic and isoluminant responses."""
        isochromatic_means = []
        isoluminant_means = []

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

            # Collect means
            isochromatic_means.extend([red_avg, green_avg, cyan_avg, orange_avg])
            isoluminant_means.extend([red_green_avg, cyan_orange_avg])

            print(f"  Individual color averages - Red: {red_avg:.2f}, Green: {green_avg:.2f}, "
                  f"Cyan: {cyan_avg:.2f}, Orange: {orange_avg:.2f}")
            print(f"  Mixed color averages - RedGreen: {red_green_avg:.2f}, CyanOrange: {cyan_orange_avg:.2f}")

        # Calculate Shannon's entropy
        def shannon_entropy(values):
            """
            Calculate Shannon's entropy: H = -Σ(p_i * log2(p_i))
            Higher entropy = more uniform distribution (less selective)
            Lower entropy = more concentrated distribution (more selective)
            """
            # Convert to numpy array and handle negative values by taking absolute
            values = np.array(values)
            values = np.abs(values)  # In case of any negative spike rates

            # If all values are zero, entropy is undefined (return 0)
            if np.sum(values) == 0:
                return 0.0

            # Normalize to probability distribution
            probabilities = values / np.sum(values)

            # Calculate entropy, handling p*log(p) for p=0 (which equals 0 by convention)
            entropy = 0.0
            for p in probabilities:
                if p > 0:  # Only include non-zero probabilities
                    entropy -= p * np.log2(p)

            return entropy

        isochromatic_entropy = shannon_entropy(isochromatic_means)
        isoluminant_entropy = shannon_entropy(isoluminant_means)

        # Calculate max possible entropy for reference
        max_isochromatic_entropy = np.log2(len(isochromatic_means))  # log2(16) = 4 bits
        max_isoluminant_entropy = np.log2(len(isoluminant_means))  # log2(8) = 3 bits

        print(f"\nShannon's Entropy calculation:")
        print(
            f"  Isochromatic - entropy: {isochromatic_entropy:.3f} bits (max possible: {max_isochromatic_entropy:.3f})")
        print(f"  Isoluminant - entropy: {isoluminant_entropy:.3f} bits (max possible: {max_isoluminant_entropy:.3f})")
        print(f"  Lower entropy = more selective (concentrated responses)")
        print(f"  Higher entropy = less selective (uniform responses)")

        return isochromatic_entropy, isoluminant_entropy

    def _calculate_mean_all_normalized(self, frequencies, get_average_for_type_and_frequency, prepared_data):
        """
        Calculate mean responses to all isochromatic and isoluminant gratings,
        normalized by the maximum response across all conditions.

        This makes the metric scale-invariant (independent of absolute firing rate).
        """
        isochromatic_all_responses = []
        isoluminant_all_responses = []

        for frequency in frequencies:
            print(f"\nProcessing frequency: {frequency}")

            # Get averages for individual colors (isochromatic)
            red_avg = get_average_for_type_and_frequency(prepared_data, 'Red', frequency)
            green_avg = get_average_for_type_and_frequency(prepared_data, 'Green', frequency)
            cyan_avg = get_average_for_type_and_frequency(prepared_data, 'Cyan', frequency)
            orange_avg = get_average_for_type_and_frequency(prepared_data, 'Orange', frequency)

            # Get averages for mixed colors (isoluminant)
            red_green_avg = get_average_for_type_and_frequency(prepared_data, 'RedGreen', frequency)
            cyan_orange_avg = get_average_for_type_and_frequency(prepared_data, 'CyanOrange', frequency)

            # Collect all responses
            isochromatic_all_responses.extend([red_avg, green_avg, cyan_avg, orange_avg])
            isoluminant_all_responses.extend([red_green_avg, cyan_orange_avg])

            print(f"  Individual color averages - Red: {red_avg:.2f}, Green: {green_avg:.2f}, "
                  f"Cyan: {cyan_avg:.2f}, Orange: {orange_avg:.2f}")
            print(f"  Mixed color averages - RedGreen: {red_green_avg:.2f}, CyanOrange: {cyan_orange_avg:.2f}")

        # Calculate mean response across ALL conditions
        isochromatic_mean = np.mean(isochromatic_all_responses)
        isoluminant_mean = np.mean(isoluminant_all_responses)

        # Find max response across ALL conditions (both isochromatic and isoluminant)
        all_responses = isochromatic_all_responses + isoluminant_all_responses
        max_response = np.max(all_responses)

        # Normalize by max response (avoid division by zero)
        if max_response == 0:
            isochromatic_normalized = 0.0
            isoluminant_normalized = 0.0
        else:
            isochromatic_normalized = isochromatic_mean / max_response
            isoluminant_normalized = isoluminant_mean / max_response

        print(f"\nNormalized mean response calculation:")
        print(f"  Isochromatic mean: {isochromatic_mean:.2f} spikes/sec")
        print(f"  Isoluminant mean: {isoluminant_mean:.2f} spikes/sec")
        print(f"  Max response (normalizer): {max_response:.2f} spikes/sec")
        print(f"  Isochromatic normalized: {isochromatic_normalized:.3f}")
        print(f"  Isoluminant normalized: {isoluminant_normalized:.3f}")

        return isochromatic_normalized, isoluminant_normalized
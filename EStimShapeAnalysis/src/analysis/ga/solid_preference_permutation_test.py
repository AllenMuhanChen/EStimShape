import numpy as np
from clat.pipeline.pipeline_base_classes import ComputationModule, InputT, OutputT, AnalysisModuleFactory, OutputHandler
from clat.util.connection import Connection


def create_sp_permutation_test_module(channel=None, session_id=None, spike_data_col=None, n_permutations=10000):
    """
    Create a module for solid preference permutation test.

    Args:
        channel: The channel/unit to analyze
        session_id: The session identifier
        spike_data_col: Column name containing spike rate data
        n_permutations: Number of permutations to run (default 10000)
    """
    permutation_module = AnalysisModuleFactory.create(
        computation=SolidPreferencePermutationTest(
            response_key=channel,
            spike_data_col=spike_data_col,
            n_permutations=n_permutations
        ),
        output_handler=SolidPreferencePermutationDBSaver(session_id, channel)
    )
    return permutation_module


class SolidPreferencePermutationDBSaver(OutputHandler):
    """Output handler that saves permutation test results to the data repository database."""

    def __init__(self, session_id: str, unit_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_columns_exist()

    def _ensure_columns_exist(self):
        """Add permutation test columns to SolidPreferenceIndices if they don't exist."""
        # Try to add each column, ignoring errors if they already exist
        columns_to_add = [
            "ALTER TABLE SolidPreferenceIndices ADD COLUMN p_value FLOAT NULL",
            "ALTER TABLE SolidPreferenceIndices ADD COLUMN n_3d_trials INT NULL",
            "ALTER TABLE SolidPreferenceIndices ADD COLUMN n_2d_trials INT NULL",
            "ALTER TABLE SolidPreferenceIndices ADD COLUMN n_permutations INT NULL"
        ]

        for sql in columns_to_add:
            try:
                self.conn.execute(sql)
            except Exception:
                # Column already exists, that's fine
                pass

    def process(self, result: dict) -> dict:
        """Save the permutation test results to the database."""
        if result is None:
            print(f"No results to save for {self.unit_name}")
            return None

        try:
            # Update the existing row with permutation test results
            update_sql = """
                         UPDATE SolidPreferenceIndices
                         SET p_value        = %s,
                             n_3d_trials    = %s,
                             n_2d_trials    = %s,
                             n_permutations = %s
                         WHERE session_id = %s \
                           AND unit_name = %s \
                         """

            n_permutations = len(result['null_distribution'])

            # Convert numpy types to Python native types
            self.conn.execute(update_sql, (
                float(result['p_value']),
                int(result['n_3d_trials']),
                int(result['n_2d_trials']),
                int(n_permutations),
                self.session_id,
                self.unit_name
            ))

            print(f"Saved permutation test results for session {self.session_id}, unit {self.unit_name}")
            print(f"  SI: {result['actual_si']:.4f}, p-value: {result['p_value']:.4f}")

        except Exception as e:
            print(f"Could not save to database (session may not be initialized): {e}")
            print(f"\nPermutation Test Results:")
            print(f"Session: {self.session_id}, Unit: {self.unit_name}")
            print(f"  Actual SI: {result['actual_si']:.4f}")
            print(f"  P-value: {result['p_value']:.4f}")
            print(f"  3D trials: {result['n_3d_trials']}, 2D trials: {result['n_2d_trials']}")
            print(f"  Permutations: {len(result['null_distribution'])}")

        return result


class SolidPreferencePermutationTest(ComputationModule):
    def __init__(self, *, response_key=None, spike_data_col="Spike Rate by channel", n_permutations=10000):
        self.response_key = response_key
        self.spike_data_col = spike_data_col
        self.n_permutations = n_permutations

    def compute(self, prepared_data: InputT) -> OutputT:
        """
        Perform permutation test for solid preference index.

        Returns:
            Dictionary containing:
                - actual_si: The real solid preference index
                - p_value: Two-tailed p-value
                - null_distribution: Array of permuted SI values
                - n_3d_trials: Number of 3D trials
                - n_2d_trials: Number of 2D trials
        """
        # Extract all trial responses
        responses_3d = self._extract_trial_responses(prepared_data, '3D')
        responses_2d = self._extract_trial_responses(prepared_data, '2D')

        if not responses_3d or not responses_2d:
            print(f"Warning: Missing data for channel {self.response_key}")
            return None

        # Calculate actual SI
        actual_si = self._calculate_si(responses_3d, responses_2d)

        # Run permutations
        null_distribution = self._run_permutations(responses_3d, responses_2d)

        # Calculate p-value
        p_value = self._calculate_p_value(actual_si, null_distribution)

        print(f"\nPermutation Test Results for {self.response_key}:")
        print(f"  Actual SI: {actual_si:.4f}")
        print(f"  P-value: {p_value:.4f}")
        print(f"  3D trials: {len(responses_3d)}, 2D trials: {len(responses_2d)}")

        return {
            'actual_si': actual_si,
            'p_value': p_value,
            'null_distribution': null_distribution,
            'n_3d_trials': len(responses_3d),
            'n_2d_trials': len(responses_2d),
            'channel': self.response_key
        }

    def _extract_trial_responses(self, data, test_type: str) -> list[float]:
        """Extract all individual trial spike rates for a given test type."""
        filtered_data = data[data['TestType'] == test_type]
        spike_rates = []

        for _, row in filtered_data.iterrows():
            spike_rate_dict = row[self.spike_data_col]
            if isinstance(spike_rate_dict, dict) and self.response_key in spike_rate_dict:
                spike_rates.append(spike_rate_dict[self.response_key])
            else:
                spike_rates.append(0.0)

        return spike_rates

    def _calculate_si(self, responses_3d: list[float], responses_2d: list[float]) -> float:
        """Calculate solid preference index."""
        total_3d = sum(responses_3d)
        total_2d = sum(responses_2d)

        if max(total_3d, total_2d) == 0:
            return 0.0

        si = (total_3d - total_2d) / max(total_3d, total_2d)
        return si

    def _run_permutations(self, responses_3d: list[float], responses_2d: list[float]) -> np.ndarray:
        """Run permutation test by shuffling labels."""
        # Combine all responses
        all_responses = responses_3d + responses_2d
        n_3d = len(responses_3d)

        # Array to store permuted SI values
        null_si_distribution = np.zeros(self.n_permutations)

        for i in range(self.n_permutations):
            # Shuffle all responses
            shuffled = np.random.permutation(all_responses)

            # Split back into two groups of original sizes
            perm_3d = shuffled[:n_3d].tolist()
            perm_2d = shuffled[n_3d:].tolist()

            # Calculate SI for this permutation
            null_si_distribution[i] = self._calculate_si(perm_3d, perm_2d)

        return null_si_distribution

    def _calculate_p_value(self, actual_si: float, null_distribution: np.ndarray) -> float:
        """
        Calculate two-tailed p-value.
        Check if actual SI is in top or bottom 2.5% of null distribution.
        """
        # Calculate percentiles
        lower_percentile = np.percentile(null_distribution, 2.5)
        upper_percentile = np.percentile(null_distribution, 97.5)

        # Two-tailed test: check if actual SI is extreme in either direction
        if actual_si <= lower_percentile or actual_si >= upper_percentile:
            # Calculate exact p-value
            # Count how many permuted values are as or more extreme
            n_more_extreme = np.sum(np.abs(null_distribution) >= np.abs(actual_si))
            p_value = n_more_extreme / len(null_distribution)
        else:
            # Not significant, calculate exact p-value
            n_more_extreme = np.sum(np.abs(null_distribution) >= np.abs(actual_si))
            p_value = n_more_extreme / len(null_distribution)

        return p_value
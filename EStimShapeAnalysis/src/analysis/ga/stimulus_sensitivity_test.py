import numpy as np
import pandas as pd
from scipy import stats
import scikit_posthocs as sp
from clat.pipeline.pipeline_base_classes import ComputationModule, AnalysisModuleFactory, OutputHandler
from clat.util.connection import Connection


class StimulusSelectivityTest(ComputationModule):
    """
    Test stimulus selectivity using Kruskal-Wallis test, with post-hoc pairwise comparisons.
    """

    def __init__(self, *, response_key=None, spike_data_col="Spike Rate by channel",
                 correction_method='fdr_bh', alpha=0.05):
        self.response_key = response_key
        self.spike_data_col = spike_data_col
        self.correction_method = correction_method
        self.alpha = alpha

    def compute(self, prepared_data):
        """
        Perform Kruskal-Wallis test and post-hoc pairwise comparisons.

        Returns:
            Dictionary containing both overall selectivity and pairwise results
        """
        # Extract responses grouped by stimulus
        responses_by_stim = self._extract_responses_by_stimulus(prepared_data, self.response_key)

        if len(responses_by_stim) < 2:
            print(f"Warning: Need at least 2 stimuli for selectivity test. Found {len(responses_by_stim)}")
            return None

        # Prepare data for Kruskal-Wallis test
        response_groups = [np.array(rates) for rates in responses_by_stim.values()]

        # Check if we have enough data
        total_trials = sum(len(group) for group in response_groups)
        if total_trials < 3:
            print(f"Warning: Need at least 3 trials total. Found {total_trials}")
            return None

        # Perform Kruskal-Wallis test
        statistic, p_value = stats.kruskal(*response_groups)
        is_selective = p_value < self.alpha

        print(f"\nStimulus Selectivity Test for {self.response_key}:")
        print(f"  H-statistic: {statistic:.4f}")
        print(f"  P-value: {p_value:.4f}")
        print(f"  Stimuli tested: {len(responses_by_stim)}")
        print(f"  Total trials: {total_trials}")
        print(f"  Selective: {'YES' if is_selective else 'NO'} (p < {self.alpha})")

        # Initialize post-hoc results
        n_comparisons = 0
        n_significant = 0
        significant_pairs = []

        # Only run post-hoc if neuron is selective
        if is_selective and len(responses_by_stim) > 2:
            print(f"\n  Running post-hoc pairwise comparisons...")

            # Prepare data for Dunn's test
            stim_ids = []
            responses = []
            for stim_id, rates in responses_by_stim.items():
                stim_ids.extend([stim_id] * len(rates))
                responses.extend(rates)

            data_df = pd.DataFrame({
                'stimulus': stim_ids,
                'response': responses
            })

            # Perform Dunn's test
            try:
                pairwise_results = sp.posthoc_dunn(
                    data_df,
                    val_col='response',
                    group_col='stimulus',
                    p_adjust=self.correction_method
                )

                # Extract significant pairs
                stim_list = list(responses_by_stim.keys())
                for i, stim1 in enumerate(stim_list):
                    for j, stim2 in enumerate(stim_list):
                        if i < j:  # Only upper triangle
                            n_comparisons += 1
                            p_val = pairwise_results.loc[stim1, stim2]

                            if p_val < self.alpha:
                                median1 = np.median(responses_by_stim[stim1])
                                median2 = np.median(responses_by_stim[stim2])

                                significant_pairs.append({
                                    'stim1': stim1,
                                    'stim2': stim2,
                                    'p_value': p_val,
                                    'median_diff': median2 - median1
                                })

                n_significant = len(significant_pairs)

                print(f"  Total pairwise comparisons: {n_comparisons}")
                print(f"  Significant pairs (p < {self.alpha}): {n_significant}")
                print(f"  Correction method: {self.correction_method}")

                if n_significant > 0:
                    print(f"\n  Top 5 most significant pairs:")
                    sorted_pairs = sorted(significant_pairs, key=lambda x: x['p_value'])[:5]
                    for pair in sorted_pairs:
                        print(f"    Stim {pair['stim1']} vs {pair['stim2']}: "
                              f"p={pair['p_value']:.4f}, Δmedian={pair['median_diff']:.2f}")

            except Exception as e:
                print(f"  Error in post-hoc test: {e}")
        elif is_selective:
            print(f"  Skipping post-hoc (only 2 stimuli)")
        else:
            print(f"  Skipping post-hoc (not selective)")

        return {
            'statistic': statistic,
            'p_value': p_value,
            'n_stimuli': len(responses_by_stim),
            'n_trials': total_trials,
            'channel': self.response_key,
            'is_selective': is_selective,
            'n_comparisons': n_comparisons,
            'n_significant': n_significant,
            'significant_pairs': significant_pairs,
            'correction_method': self.correction_method
        }

    def _extract_responses_by_stimulus(self, data: pd.DataFrame, channel: str) -> dict:
        """Extract spike rates grouped by stimulus."""
        responses_by_stim = {}

        for stim_id in data['StimSpecId'].unique():
            stim_trials = data[data['StimSpecId'] == stim_id]
            spike_rates = []

            for _, trial in stim_trials.iterrows():
                spike_rate_dict = trial[self.spike_data_col]
                if isinstance(spike_rate_dict, dict) and channel in spike_rate_dict:
                    spike_rates.append(spike_rate_dict[channel])

            if spike_rates:
                responses_by_stim[stim_id] = spike_rates

        return responses_by_stim


class StimulusSelectivityDBSaver(OutputHandler):
    """Output handler that saves stimulus selectivity and post-hoc test results."""

    def __init__(self, session_id: str, unit_name: str):
        self.unit_name = unit_name
        self.session_id = session_id
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the StimulusSelectivity table with post-hoc columns."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS StimulusSelectivity \
                           ( \
                               session_id        VARCHAR(10)  NOT NULL, \
                               unit_name         VARCHAR(255) NOT NULL, \
                               h_statistic       FLOAT        NOT NULL, \
                               p_value           FLOAT        NOT NULL, \
                               n_stimuli         INT          NOT NULL, \
                               n_trials          INT          NOT NULL, \
                               is_selective      BOOLEAN      NOT NULL, \
                               n_comparisons     INT          NOT NULL DEFAULT 0, \
                               n_significant     INT          NOT NULL DEFAULT 0, \
                               correction_method VARCHAR(50)  NULL, \
                               PRIMARY KEY (session_id, unit_name), \
                               CONSTRAINT StimulusSelectivity_ibfk_1 \
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id) \
                                       ON DELETE CASCADE
                           ) CHARSET = latin1; \
                           """
        self.conn.execute(create_table_sql)

    def process(self, result: dict) -> dict:
        """Save the stimulus selectivity and post-hoc results to the database."""
        if result is None:
            print(f"No results to save for {self.unit_name}")
            return None

        try:
            insert_sql = """
                         INSERT INTO StimulusSelectivity
                         (session_id, unit_name, h_statistic, p_value, n_stimuli, n_trials,
                          is_selective, n_comparisons, n_significant, correction_method)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                         ON DUPLICATE KEY UPDATE h_statistic       = VALUES(h_statistic), \
                                                 p_value           = VALUES(p_value), \
                                                 n_stimuli         = VALUES(n_stimuli), \
                                                 n_trials          = VALUES(n_trials), \
                                                 is_selective      = VALUES(is_selective), \
                                                 n_comparisons     = VALUES(n_comparisons), \
                                                 n_significant     = VALUES(n_significant), \
                                                 correction_method = VALUES(correction_method) \
                         """

            self.conn.execute(insert_sql, (
                self.session_id,
                self.unit_name,
                float(result['statistic']),
                float(result['p_value']),
                int(result['n_stimuli']),
                int(result['n_trials']),
                bool(result['is_selective']),
                int(result['n_comparisons']),
                int(result['n_significant']),
                result['correction_method']
            ))

            print(f"\nSaved selectivity test results for session {self.session_id}, unit {self.unit_name}")
            print(
                f"  Selective: {result['is_selective']}, Post-hoc: {result['n_significant']}/{result['n_comparisons']} pairs")

        except Exception as e:
            print(f"Could not save to database (session may not be initialized): {e}")
            print(f"\nStimulus Selectivity Test Results:")
            print(f"Session: {self.session_id}, Unit: {self.unit_name}")
            print(f"  H-statistic: {result['statistic']:.4f}")
            print(f"  P-value: {result['p_value']:.4f}")
            print(f"  Selective: {result['is_selective']}")
            print(f"  Significant pairs: {result['n_significant']}/{result['n_comparisons']}")

        return result


def create_stimulus_selectivity_module(channel=None, session_id=None, spike_data_col=None,
                                       correction_method='fdr_bh'):
    """Create a module for stimulus selectivity test with post-hoc comparisons."""
    selectivity_module = AnalysisModuleFactory.create(
        computation=StimulusSelectivityTest(
            response_key=channel,
            spike_data_col=spike_data_col,
            correction_method=correction_method
        ),
        output_handler=StimulusSelectivityDBSaver(session_id, channel)
    )
    return selectivity_module
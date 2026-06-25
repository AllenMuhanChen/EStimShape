import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from clat.pipeline.pipeline_base_classes import ComputationModule, AnalysisModuleFactory, OutputHandler
from clat.util.connection import Connection


class PreferredOrientationCalculator(ComputationModule):
    """Calculate orientation tuning for a unit at each spatial frequency.

    For each frequency we pick the *best* stimulus type (the color/type with the
    highest mean response across orientations at that frequency) and then describe
    that type's orientation tuning:
        - the preferred (highest-responding) orientation
        - the full vector of responses across all orientations
        - the max-minus-min response across orientations (tuning depth)

    Not every experiment has orientation data. If the orientation column is
    missing (or contains no usable values) this returns ``None`` instead of
    crashing, so it can be dropped into a pipeline safely.
    """

    def __init__(self, *, response_key=None, spike_data_col="Spike Rate by channel",
                 type_col='Type', frequency_col='Frequency', orientation_col='Orientation',
                 filter_values=None):
        self.response_key = response_key
        self.spike_data_col = spike_data_col
        self.type_col = type_col
        self.frequency_col = frequency_col
        self.orientation_col = orientation_col
        self.filter_values = filter_values or {}

    def compute(self, prepared_data):
        # Filter data if specified
        data = prepared_data.copy()
        for col, values in self.filter_values.items():
            if col in data.columns:
                data = data[data[col].isin(values)]

        # Gracefully skip experiments that have no orientation data at all
        if self.orientation_col not in data.columns:
            print(f"No '{self.orientation_col}' column found - skipping preferred "
                  f"orientation analysis for {self.response_key}")
            return None

        # Extract spike rates / type / frequency / orientation for this channel
        spike_rates = []
        types = []
        frequencies = []
        orientations = []

        for _, row in data.iterrows():
            spike_rate_dict = row[self.spike_data_col]
            orientation = row[self.orientation_col]

            # Skip rows without a usable orientation value
            if orientation is None or (isinstance(orientation, float) and np.isnan(orientation)):
                continue
            try:
                orientation_val = float(orientation)
            except (TypeError, ValueError):
                continue

            if isinstance(spike_rate_dict, dict) and self.response_key in spike_rate_dict:
                spike_rates.append(spike_rate_dict[self.response_key])
                types.append(row[self.type_col])
                frequencies.append(row[self.frequency_col])
                orientations.append(orientation_val)

        df = pd.DataFrame({
            'Type': types,
            'Frequency': frequencies,
            'Orientation': orientations,
            'SpikeRate': spike_rates
        })

        if df.empty:
            print(f"No orientation data found for channel {self.response_key} - "
                  f"skipping preferred orientation analysis")
            return None

        # Average spike rate for each Type / Frequency / Orientation combination
        grouped = df.groupby(['Type', 'Frequency', 'Orientation'])['SpikeRate'].mean().reset_index()

        per_frequency = {}
        for frequency in sorted(grouped['Frequency'].unique()):
            freq_data = grouped[grouped['Frequency'] == frequency]

            # Best type at this frequency = type with the highest mean response
            # across all of its orientations.
            type_means = freq_data.groupby('Type')['SpikeRate'].mean()
            best_type = type_means.idxmax()

            best_type_data = freq_data[freq_data['Type'] == best_type].sort_values('Orientation')

            # Skip frequencies that only have a single orientation - there is no
            # tuning curve to describe.
            if best_type_data['Orientation'].nunique() < 2:
                print(f"\nSkipping {frequency} cycles/° for {self.response_key}: "
                      f"only one orientation tested")
                continue

            # Vector of responses across all orientations (for the best type)
            orientation_responses = {float(o): float(r) for o, r in
                                     zip(best_type_data['Orientation'], best_type_data['SpikeRate'])}

            preferred_idx = best_type_data['SpikeRate'].idxmax()
            preferred_orientation = float(best_type_data.loc[preferred_idx, 'Orientation'])
            max_response = float(best_type_data['SpikeRate'].max())
            min_response = float(best_type_data['SpikeRate'].min())
            max_minus_min = max_response - min_response

            per_frequency[float(frequency)] = {
                'preferred_orientation': preferred_orientation,
                'best_type': str(best_type),
                'max_response': max_response,
                'max_minus_min': max_minus_min,
                'orientation_responses': orientation_responses,
            }

            print(f"\nPreferred Orientation for {self.response_key} at {frequency} cycles/°:")
            print(f"  Best type: {best_type}")
            print(f"  Preferred orientation: {preferred_orientation}")
            print(f"  Max response: {max_response:.2f} spikes/s")
            print(f"  Max-min (tuning depth): {max_minus_min:.2f} spikes/s")
            print(f"  Orientation responses: {orientation_responses}")

        return {
            'channel': self.response_key,
            'per_frequency': per_frequency,
        }


class PreferredOrientationOutputHandler(OutputHandler):
    """Save preferred orientation results to the database and plot the tuning curves."""

    def __init__(self, session_id: str, unit_name: str, save_path: str = None):
        self.unit_name = unit_name
        self.session_id = session_id
        self.save_path = save_path
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the PreferredOrientations table if it doesn't exist."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS PreferredOrientations
                           (
                               session_id            VARCHAR(10)  NOT NULL,
                               unit_name             VARCHAR(255) NOT NULL,
                               frequency             FLOAT        NOT NULL,
                               preferred_orientation FLOAT        NOT NULL,
                               best_type             VARCHAR(50)  NOT NULL,
                               max_response          FLOAT        NOT NULL,
                               max_minus_min         FLOAT        NOT NULL,
                               orientation_responses TEXT         NULL,
                               PRIMARY KEY (session_id, unit_name, frequency),
                               CONSTRAINT PreferredOrientations_ibfk_1
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id)
                                       ON DELETE CASCADE
                           ) CHARSET = latin1;
                           """
        self.conn.execute(create_table_sql)

    def _clear_session_data(self):
        """Delete existing entries for this session and unit so stale frequencies don't linger."""
        delete_sql = "DELETE FROM PreferredOrientations WHERE session_id = %s AND unit_name = %s"
        self.conn.execute(delete_sql, (self.session_id, self.unit_name))
        print(f"Cleared existing Preferred Orientation data for session {self.session_id}, "
              f"unit {self.unit_name}")

    def process(self, result: dict) -> dict:
        if result is None:
            print(f"No preferred orientation results to save for {self.unit_name}")
            return None

        per_frequency = result['per_frequency']

        try:
            self._clear_session_data()
            for frequency, freq_result in per_frequency.items():
                orientation_json = json.dumps(freq_result['orientation_responses'])
                insert_sql = """
                             INSERT INTO PreferredOrientations
                             (session_id, unit_name, frequency, preferred_orientation, best_type,
                              max_response, max_minus_min, orientation_responses)
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                             ON DUPLICATE KEY UPDATE preferred_orientation = VALUES(preferred_orientation),
                                                     best_type             = VALUES(best_type),
                                                     max_response          = VALUES(max_response),
                                                     max_minus_min         = VALUES(max_minus_min),
                                                     orientation_responses = VALUES(orientation_responses)
                             """
                self.conn.execute(insert_sql, (
                    self.session_id,
                    self.unit_name,
                    float(frequency),
                    float(freq_result['preferred_orientation']),
                    str(freq_result['best_type']),
                    float(freq_result['max_response']),
                    float(freq_result['max_minus_min']),
                    orientation_json,
                ))
                print(f"Saved preferred orientation for session {self.session_id}, "
                      f"unit {self.unit_name}, frequency {frequency}")
        except Exception as e:
            print(f"Could not save preferred orientation to database "
                  f"(session may not be initialized): {e}")

        self._plot(result)
        return result

    def _plot(self, result: dict):
        """Plot orientation tuning curves per frequency and the max-min response per frequency."""
        per_frequency = result['per_frequency']
        channel = result['channel']

        if not per_frequency:
            print("No per-frequency data to plot")
            return

        frequencies = sorted(per_frequency.keys())

        fig, (ax_tuning, ax_depth) = plt.subplots(1, 2, figsize=(14, 6))

        # --- Plot 1: orientation tuning curves, one line per frequency ---
        cmap = plt.get_cmap('viridis')
        for i, frequency in enumerate(frequencies):
            orientation_responses = per_frequency[frequency]['orientation_responses']
            orientations = sorted(orientation_responses.keys())
            responses = [orientation_responses[o] for o in orientations]
            color = cmap(i / max(len(frequencies) - 1, 1))
            ax_tuning.plot(orientations, responses, marker='o', linewidth=2,
                           color=color, label=f"{frequency:g} cyc/°")

        ax_tuning.set_xlabel('Orientation (°)', fontsize=12)
        ax_tuning.set_ylabel('Average Spike Rate (spikes/s)', fontsize=12)
        ax_tuning.set_title(f'Orientation Tuning by Frequency: {channel}', fontsize=13)
        ax_tuning.legend(title='Frequency', loc='best', framealpha=0.9)
        ax_tuning.grid(True, alpha=0.3)

        # --- Plot 2: max-min orientation response per frequency ---
        max_minus_min = [per_frequency[f]['max_minus_min'] for f in frequencies]
        ax_depth.bar([f"{f:g}" for f in frequencies], max_minus_min, color='steelblue', alpha=0.8)
        ax_depth.set_xlabel('Frequency (cycles/°)', fontsize=12)
        ax_depth.set_ylabel('Max - Min Response (spikes/s)', fontsize=12)
        ax_depth.set_title(f'Orientation Tuning Depth by Frequency: {channel}', fontsize=13)
        ax_depth.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if self.save_path:
            plt.savefig(self.save_path, dpi=300, bbox_inches='tight')
            print(f"Saved preferred orientation plot: {self.save_path}")


def create_preferred_orientation_module(channel=None, session_id=None, spike_data_col=None,
                                        filter_values=None, save_path=None):
    """
    Create a module for calculating preferred orientation at each frequency.

    Args:
        channel: Channel/unit to analyze
        session_id: Session identifier
        spike_data_col: Column containing spike rate data
        filter_values: Dictionary of column:values to filter data
        save_path: Path to save the orientation tuning plot
    """
    pref_orientation_module = AnalysisModuleFactory.create(
        computation=PreferredOrientationCalculator(
            response_key=channel,
            spike_data_col=spike_data_col,
            filter_values=filter_values
        ),
        output_handler=PreferredOrientationOutputHandler(session_id, channel, save_path=save_path)
    )
    return pref_orientation_module

import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from clat.pipeline.pipeline_base_classes import ComputationModule, AnalysisModuleFactory, OutputHandler
from clat.util.connection import Connection


# Canonical ordering / display colours for the gabor "colors" (types). Isochromatic
# and isoluminant gabors are pooled together here - they are just different colors.
TYPE_ORDER = ['Red', 'Green', 'Cyan', 'Orange', 'RedGreen', 'CyanOrange']
TYPE_DISPLAY_COLORS = {
    'Red': 'red',
    'Green': 'green',
    'Cyan': 'cyan',
    'Orange': 'orange',
    'RedGreen': 'darkred',
    'CyanOrange': 'teal',
}


class PreferredColorCalculator(ComputationModule):
    """Calculate colour preference for a unit at each spatial frequency.

    The "colors" are the gabor types (Red, Green, Cyan, Orange, RedGreen,
    CyanOrange) - isochromatic and isoluminant gabors are pooled together. For
    each frequency we describe the unit's colour tuning across types (averaging
    over orientations / repeats):
        - the preferred (highest-responding) colour
        - the full vector of responses across all colours
        - the max-minus-min response across colours (tuning depth)
    """

    def __init__(self, *, response_key=None, spike_data_col="Spike Rate by channel",
                 type_col='Type', frequency_col='Frequency', filter_values=None):
        self.response_key = response_key
        self.spike_data_col = spike_data_col
        self.type_col = type_col
        self.frequency_col = frequency_col
        self.filter_values = filter_values or {}

    def compute(self, prepared_data):
        # Filter data if specified
        data = prepared_data.copy()
        for col, values in self.filter_values.items():
            if col in data.columns:
                data = data[data[col].isin(values)]

        # Extract spike rates / type / frequency for this channel
        spike_rates = []
        types = []
        frequencies = []

        for _, row in data.iterrows():
            spike_rate_dict = row[self.spike_data_col]
            if isinstance(spike_rate_dict, dict) and self.response_key in spike_rate_dict:
                spike_rates.append(spike_rate_dict[self.response_key])
                types.append(row[self.type_col])
                frequencies.append(row[self.frequency_col])

        df = pd.DataFrame({
            'Type': types,
            'Frequency': frequencies,
            'SpikeRate': spike_rates
        })

        if df.empty:
            print(f"No colour data found for channel {self.response_key} - "
                  f"skipping preferred colour analysis")
            return None

        # Average spike rate for each Type / Frequency combination (pools orientations / repeats)
        grouped = df.groupby(['Type', 'Frequency'])['SpikeRate'].mean().reset_index()

        per_frequency = {}
        for frequency in sorted(grouped['Frequency'].unique()):
            freq_data = grouped[grouped['Frequency'] == frequency]

            # Skip frequencies that only have a single colour - there is no
            # colour tuning to describe.
            if freq_data['Type'].nunique() < 2:
                print(f"\nSkipping {frequency} cycles/° for {self.response_key}: "
                      f"only one colour tested")
                continue

            # Vector of responses across all colours, in canonical order
            color_responses = {str(t): float(r) for t, r in
                               zip(freq_data['Type'], freq_data['SpikeRate'])}
            color_responses = {t: color_responses[t] for t in TYPE_ORDER if t in color_responses}

            preferred_idx = freq_data['SpikeRate'].idxmax()
            preferred_color = str(freq_data.loc[preferred_idx, 'Type'])
            max_response = float(freq_data['SpikeRate'].max())
            min_response = float(freq_data['SpikeRate'].min())
            max_minus_min = max_response - min_response

            per_frequency[float(frequency)] = {
                'preferred_color': preferred_color,
                'max_response': max_response,
                'max_minus_min': max_minus_min,
                'color_responses': color_responses,
            }

            print(f"\nPreferred Colour for {self.response_key} at {frequency} cycles/°:")
            print(f"  Preferred colour: {preferred_color}")
            print(f"  Max response: {max_response:.2f} spikes/s")
            print(f"  Max-min (tuning depth): {max_minus_min:.2f} spikes/s")
            print(f"  Colour responses: {color_responses}")

        return {
            'channel': self.response_key,
            'per_frequency': per_frequency,
        }


class PreferredColorOutputHandler(OutputHandler):
    """Save preferred colour results to the database and plot the colour tuning."""

    def __init__(self, session_id: str, unit_name: str, save_path: str = None):
        self.unit_name = unit_name
        self.session_id = session_id
        self.save_path = save_path
        self.conn = Connection("allen_data_repository")
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create the PreferredColors table if it doesn't exist."""
        create_table_sql = """
                           CREATE TABLE IF NOT EXISTS PreferredColors
                           (
                               session_id      VARCHAR(10)  NOT NULL,
                               unit_name       VARCHAR(255) NOT NULL,
                               frequency       FLOAT        NOT NULL,
                               preferred_color VARCHAR(50)  NOT NULL,
                               max_response    FLOAT        NOT NULL,
                               max_minus_min   FLOAT        NOT NULL,
                               color_responses TEXT         NULL,
                               PRIMARY KEY (session_id, unit_name, frequency),
                               CONSTRAINT PreferredColors_ibfk_1
                                   FOREIGN KEY (session_id) REFERENCES Sessions (session_id)
                                       ON DELETE CASCADE
                           ) CHARSET = latin1;
                           """
        self.conn.execute(create_table_sql)

    def _clear_session_data(self):
        """Delete existing entries for this session and unit so stale frequencies don't linger."""
        delete_sql = "DELETE FROM PreferredColors WHERE session_id = %s AND unit_name = %s"
        self.conn.execute(delete_sql, (self.session_id, self.unit_name))
        print(f"Cleared existing Preferred Colour data for session {self.session_id}, "
              f"unit {self.unit_name}")

    def process(self, result: dict) -> dict:
        if result is None:
            print(f"No preferred colour results to save for {self.unit_name}")
            return None

        per_frequency = result['per_frequency']

        try:
            self._clear_session_data()
            for frequency, freq_result in per_frequency.items():
                color_json = json.dumps(freq_result['color_responses'])
                insert_sql = """
                             INSERT INTO PreferredColors
                             (session_id, unit_name, frequency, preferred_color,
                              max_response, max_minus_min, color_responses)
                             VALUES (%s, %s, %s, %s, %s, %s, %s)
                             ON DUPLICATE KEY UPDATE preferred_color = VALUES(preferred_color),
                                                     max_response    = VALUES(max_response),
                                                     max_minus_min   = VALUES(max_minus_min),
                                                     color_responses = VALUES(color_responses)
                             """
                self.conn.execute(insert_sql, (
                    self.session_id,
                    self.unit_name,
                    float(frequency),
                    str(freq_result['preferred_color']),
                    float(freq_result['max_response']),
                    float(freq_result['max_minus_min']),
                    color_json,
                ))
                print(f"Saved preferred colour for session {self.session_id}, "
                      f"unit {self.unit_name}, frequency {frequency}")
        except Exception as e:
            print(f"Could not save preferred colour to database "
                  f"(session may not be initialized): {e}")

        self._plot(result)
        return result

    def _plot(self, result: dict):
        """Plot colour tuning per frequency and the max-min response per frequency."""
        per_frequency = result['per_frequency']
        channel = result['channel']

        if not per_frequency:
            print("No per-frequency data to plot")
            return

        frequencies = sorted(per_frequency.keys())

        fig, (ax_tuning, ax_depth) = plt.subplots(1, 2, figsize=(14, 6))

        # --- Plot 1: colour tuning curves, one line per frequency ---
        cmap = plt.get_cmap('viridis')
        for i, frequency in enumerate(frequencies):
            color_responses = per_frequency[frequency]['color_responses']
            colors = [t for t in TYPE_ORDER if t in color_responses]
            responses = [color_responses[t] for t in colors]
            color = cmap(i / max(len(frequencies) - 1, 1))
            ax_tuning.plot(colors, responses, marker='o', linewidth=2,
                           color=color, label=f"{frequency:g} cyc/°")

        ax_tuning.set_xlabel('Colour (gabor type)', fontsize=12)
        ax_tuning.set_ylabel('Average Spike Rate (spikes/s)', fontsize=12)
        ax_tuning.set_title(f'Colour Tuning by Frequency: {channel}', fontsize=13)
        ax_tuning.legend(title='Frequency', loc='best', framealpha=0.9)
        ax_tuning.grid(True, alpha=0.3)
        ax_tuning.tick_params(axis='x', rotation=45)

        # --- Plot 2: max-min colour response per frequency ---
        max_minus_min = [per_frequency[f]['max_minus_min'] for f in frequencies]
        ax_depth.bar([f"{f:g}" for f in frequencies], max_minus_min, color='steelblue', alpha=0.8)
        ax_depth.set_xlabel('Frequency (cycles/°)', fontsize=12)
        ax_depth.set_ylabel('Max - Min Response (spikes/s)', fontsize=12)
        ax_depth.set_title(f'Colour Tuning Depth by Frequency: {channel}', fontsize=13)
        ax_depth.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if self.save_path:
            plt.savefig(self.save_path, dpi=300, bbox_inches='tight')
            print(f"Saved preferred colour plot: {self.save_path}")


def create_preferred_color_module(channel=None, session_id=None, spike_data_col=None,
                                  filter_values=None, save_path=None):
    """
    Create a module for calculating preferred colour at each frequency.

    Args:
        channel: Channel/unit to analyze
        session_id: Session identifier
        spike_data_col: Column containing spike rate data
        filter_values: Dictionary of column:values to filter data
        save_path: Path to save the colour tuning plot
    """
    pref_color_module = AnalysisModuleFactory.create(
        computation=PreferredColorCalculator(
            response_key=channel,
            spike_data_col=spike_data_col,
            filter_values=filter_values
        ),
        output_handler=PreferredColorOutputHandler(session_id, channel, save_path=save_path)
    )
    return pref_color_module

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from clat.pipeline.pipeline_base_classes import ComputationModule, AnalysisModuleFactory, OutputHandler


class FrequencyResponsePlotter(ComputationModule):
    """Plot average spike rate vs frequency for each stimulus type."""

    def __init__(self, *, response_key=None, spike_data_col="Spike Rate by channel",
                 type_col='Type', frequency_col='Frequency', filter_values=None):
        self.response_key = response_key
        self.spike_data_col = spike_data_col
        self.type_col = type_col
        self.frequency_col = frequency_col
        self.filter_values = filter_values or {}

    def compute(self, prepared_data):
        """
        Compute average responses by frequency for each type.

        Returns:
            Dictionary with plotting data
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

        # Create DataFrame for easier grouping
        df = pd.DataFrame({
            'Type': types,
            'Frequency': frequencies,
            'SpikeRate': spike_rates
        })

        if df.empty:
            print(f"No data found for channel {self.response_key}")
            return None

        # Calculate average spike rate for each Type-Frequency combination
        grouped_data = df.groupby([self.type_col, self.frequency_col])['SpikeRate'].agg(
            ['mean', 'std', 'count']).reset_index()

        # Calculate combined average across all types for each frequency
        combined_data = df.groupby(self.frequency_col)['SpikeRate'].agg(['mean', 'std', 'count']).reset_index()
        combined_data['Type'] = 'Combined'

        print(f"\nFrequency Response for {self.response_key}:")
        print(f"  Types: {sorted(df['Type'].unique())}")
        print(f"  Frequencies: {sorted(df['Frequency'].unique())}")
        print(f"  Total trials: {len(df)}")

        return {
            'grouped_data': grouped_data,
            'combined_data': combined_data,
            'channel': self.response_key,
            'raw_data': df
        }


class FrequencyResponsePlotSaver(OutputHandler):
    """Save frequency response plot."""

    def __init__(self, title=None, save_path=None, colors=None):
        self.title = title or "Frequency Response"
        self.save_path = save_path
        self.colors = colors or {
            'Red': 'red',
            'Green': 'green',
            'RedGreen': 'darkred',
            'Cyan': 'cyan',
            'Orange': 'orange',
            'CyanOrange': 'teal',
            'Combined': 'black'
        }

    def process(self, result):
        """Create and save the frequency response plot."""
        if result is None:
            print("No data to plot")
            return None

        grouped_data = result['grouped_data']
        combined_data = result['combined_data']
        channel = result['channel']

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Get unique types and frequencies
        types = sorted(grouped_data['Type'].unique())
        frequencies = sorted(grouped_data['Frequency'].unique())

        # Plot each type
        for stimulus_type in types:
            type_data = grouped_data[grouped_data['Type'] == stimulus_type].sort_values('Frequency')

            color = self.colors.get(stimulus_type, 'gray')

            # Plot mean line
            ax.plot(type_data['Frequency'], type_data['mean'],
                    marker='o', linewidth=2, label=stimulus_type,
                    color=color, alpha=0.7)

            # Add error bars (standard error of the mean)
            if 'std' in type_data.columns and 'count' in type_data.columns:
                sem = type_data['std'] / np.sqrt(type_data['count'])
                ax.fill_between(type_data['Frequency'],
                                type_data['mean'] - sem,
                                type_data['mean'] + sem,
                                color=color, alpha=0.2)

        # Plot combined average with thicker line
        combined_sorted = combined_data.sort_values('Frequency')
        ax.plot(combined_sorted['Frequency'], combined_sorted['mean'],
                marker='s', linewidth=3, label='Combined',
                color=self.colors.get('Combined', 'black'),
                linestyle='--', alpha=0.9)

        # Add combined error bars
        if 'std' in combined_sorted.columns and 'count' in combined_sorted.columns:
            sem = combined_sorted['std'] / np.sqrt(combined_sorted['count'])
            ax.fill_between(combined_sorted['Frequency'],
                            combined_sorted['mean'] - sem,
                            combined_sorted['mean'] + sem,
                            color=self.colors.get('Combined', 'black'),
                            alpha=0.1)

        # Formatting
        ax.set_xlabel('Frequency (cycles/°)', fontsize=12)
        ax.set_ylabel('Average Spike Rate (spikes/s)', fontsize=12)
        ax.set_title(f'{self.title}: {channel}', fontsize=14)
        ax.legend(loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)

        # Set x-axis to log scale if frequencies span multiple orders of magnitude
        freq_range = max(frequencies) / min(frequencies) if min(frequencies) > 0 else 1
        if freq_range > 10:
            ax.set_xscale('log')

        plt.tight_layout()

        # Save if path provided
        if self.save_path:
            plt.savefig(self.save_path, dpi=300, bbox_inches='tight')
            print(f"Saved frequency response plot: {self.save_path}")

        return result


def create_frequency_response_module(channel=None, spike_data_col=None,
                                     filter_values=None, title=None, save_path=None,
                                     colors=None):
    """
    Create a module for plotting frequency response curves.

    Args:
        channel: Channel/unit to analyze
        spike_data_col: Column containing spike rate data
        filter_values: Dictionary of column:values to filter data
        title: Plot title
        save_path: Path to save the plot
        colors: Dictionary mapping stimulus types to colors
    """
    freq_response_module = AnalysisModuleFactory.create(
        computation=FrequencyResponsePlotter(
            response_key=channel,
            spike_data_col=spike_data_col,
            filter_values=filter_values
        ),
        output_handler=FrequencyResponsePlotSaver(
            title=title,
            save_path=save_path,
            colors=colors
        )
    )
    return freq_response_module
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.gridspec import GridSpec
from typing import Dict, List, Any
from clat.util.connection import Connection
from clat.compile.trial.trial_collector import TrialCollector
from clat.compile.task.compile_task_id import TaskIdCollector
from src.analysis.grouped_rasters import GroupedRasterInputHandler, GroupedRasterPlotter, GroupedRasterOutput, \
    create_grouped_raster_pipeline
from src.intan.MultiFileParser import MultiFileParser
from src.startup import context
from src.analysis.isogabor.isogabor_analysis import TypeField, FrequencyField, IntanSpikesByChannelField
# Import our pipeline framework
from src.analysis.pipeline import (
    InputHandler, ComputationModule, OutputHandler, create_pipeline, AnalysisModuleFactory
)


def main():
    # ----------------
    # STEP 1: Compile data
    # ----------------
    conn = Connection(context.isogabor_database)
    trial_collector = TrialCollector(conn)
    trial_tstamps = trial_collector.collect_trials()
    compiled_data = compile_data(conn, trial_tstamps)

    # ----------------
    # STEP 2: Create and run the analysis pipeline
    # ----------------
    # For the isochromatic/isoluminant example:
    pipeline = create_grouped_raster_pipeline(
        primary_group_col='Type',
        secondary_group_col='Frequency',
        filter_values={
            'Type': ['Red', 'Green', 'Cyan', 'Blue', 'RedGreen', 'CyanOrange']
        },
        save_path=None
    )

    # Run the pipeline
    result = pipeline.run(compiled_data)

    # Show the figure
    plt.show()

    return result


class RasterInputHandler(InputHandler):
    """Input handler for raster plot analysis that works with compiled data"""

    def __init__(self, isochromatic_types: List[str], isoluminant_types: List[str]):
        """Initialize with the stimulus type groupings"""
        self.isochromatic_types = isochromatic_types
        self.isoluminant_types = isoluminant_types

    def prepare(self, compiled_data: pd.DataFrame) -> Dict[str, Any]:
        """Prepare the compiled data for raster plot visualization"""
        # Filter data by stimulus types
        isochromatic_data = compiled_data[compiled_data['Type'].isin(self.isochromatic_types)]
        isoluminant_data = compiled_data[compiled_data['Type'].isin(self.isoluminant_types)]

        return {
            'full_data': compiled_data,
            'isochromatic_data': isochromatic_data,
            'isoluminant_data': isoluminant_data
        }


class RasterPlotComputation(ComputationModule):
    """Compute raster plot positions and organization"""

    def compute(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """Organize data for raster plotting"""
        result = {
            'full_data': prepared_data['full_data'],
            'isochromatic': self._compute_group_data(
                prepared_data['isochromatic_data'],
                [t for t in self._get_types(prepared_data['isochromatic_data'])]
            ),
            'isoluminant': self._compute_group_data(
                prepared_data['isoluminant_data'],
                [t for t in self._get_types(prepared_data['isoluminant_data'])]
            )
        }
        return result

    def _get_types(self, data: pd.DataFrame) -> List[str]:
        """Get unique stimulus types in the data"""
        return sorted(data['Type'].unique())

    def _compute_group_data(self, data: pd.DataFrame, types: List[str]) -> Dict[str, Any]:
        """Compute plotting information for a stimulus group"""
        current_y = 0
        type_positions = {}
        frequency_positions = {}
        trial_y_positions = {}

        for stim_type in types:
            type_data = data[data['Type'] == stim_type]
            type_trial_count = 0

            # Skip empty types
            if len(type_data) == 0:
                continue

            frequencies = sorted(type_data['Frequency'].unique())
            frequency_positions[stim_type] = {}
            trial_y_positions[stim_type] = {}

            for freq in frequencies:
                freq_data = type_data[type_data['Frequency'] == freq]
                trial_count = len(freq_data)
                type_trial_count += trial_count

                # Store the center position for this frequency's trials
                frequency_positions[stim_type][freq] = current_y + trial_count / 2

                # Store y-position for each trial
                trial_y_positions[stim_type][freq] = []
                for i in range(trial_count):
                    trial_y_positions[stim_type][freq].append(current_y)
                    current_y += 1

            # Store the center position for this stimulus type
            if type_trial_count > 0:
                type_positions[stim_type] = current_y - type_trial_count / 2
                current_y += 1  # Add space between stimulus types

        return {
            'data': data,
            'types': types,
            'total_height': current_y,
            'type_positions': type_positions,
            'frequency_positions': frequency_positions,
            'trial_y_positions': trial_y_positions
        }


class RasterPlotOutput(OutputHandler):
    """Generate raster plot visualization"""

    def __init__(self, figsize=(15, 10), save_path=None):
        self.figsize = figsize
        self.save_path = save_path

    def process(self, result: Dict[str, Any]) -> plt.Figure:
        """Create the raster plot figure"""
        # Create figure with two subfigures
        fig = plt.figure(figsize=self.figsize)

        # Set up grid with appropriate height ratios
        iso_heights = [
            max(1, result['isochromatic']['total_height']),
            max(1, result['isoluminant']['total_height'])
        ]
        gs = GridSpec(2, 1, height_ratios=iso_heights)

        # Create subplots
        ax1 = fig.add_subplot(gs[0])
        self._plot_group(result['isochromatic'], ax1, "Isochromatic Stimuli")

        ax2 = fig.add_subplot(gs[1])
        self._plot_group(result['isoluminant'], ax2, "Isoluminant Stimuli")

        plt.tight_layout()

        # Save if requested
        if self.save_path:
            fig.savefig(self.save_path, dpi=300, bbox_inches='tight')

        return fig

    def _plot_group(self, group_data, ax, title):
        """Plot a single stimulus group"""
        data = group_data['data']

        # Get plotting positions
        type_positions = group_data['type_positions']
        freq_positions = group_data['frequency_positions']

        # Plot each stimulus type
        for stim_type in group_data['types']:
            # Skip if no data for this type
            if stim_type not in type_positions:
                continue

            type_data = data[data['Type'] == stim_type]

            # Plot each frequency
            for freq in sorted(type_data['Frequency'].unique()):
                freq_data = type_data[type_data['Frequency'] == freq]

                # Plot each trial
                for i, (_, trial) in enumerate(freq_data.iterrows()):
                    y_pos = group_data['trial_y_positions'][stim_type][freq][i]

                    # Plot spikes for each channel
                    spikes_by_channel = trial['Spikes by Channel']
                    for channel, spike_times in spikes_by_channel.items():
                        ax.vlines(spike_times, y_pos, y_pos + 0.9, color='black', lw=0.5)

        # Add labels
        self._add_labels(ax, type_positions, freq_positions)

        # Set up plot
        ax.set_title(title)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Trials')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Set limits
        ax.set_ylim(-0.5, group_data['total_height'] + 0.5)
        ax.set_xlim(0, 0.5)  # Adjust based on trial duration

    def _add_labels(self, ax, type_positions, freq_positions):
        """Add type and frequency labels to the plot"""
        # Add stimulus type labels
        for stim_type, pos in type_positions.items():
            ax.text(1.15, pos, stim_type, transform=ax.get_yaxis_transform(),
                    verticalalignment='center', fontweight='bold')

        # Add frequency labels
        for stim_type, freqs in freq_positions.items():
            for freq, pos in freqs.items():
                ax.text(1.02, pos, f'{freq} Hz', transform=ax.get_yaxis_transform(),
                        verticalalignment='center', fontsize=8)

    # Define a function that uses your existing compilation system


def compile_data(conn, trial_tstamps):
    # Set up your existing fields
    from clat.compile.trial.cached_fields import CachedFieldList
    from src.analysis.cached_fields import TaskIdField, StimIdField

    # Import your field classes

    # Set up parser
    task_ids = TaskIdCollector(conn).collect_task_ids()
    parser = MultiFileParser(to_cache=True, cache_dir=context.isogabor_parsed_spikes_path)

    # Create fields list
    fields = CachedFieldList()
    fields.append(TaskIdField(conn))
    fields.append(StimIdField(conn))
    fields.append(TypeField(conn))
    fields.append(FrequencyField(conn))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.isogabor_intan_path))

    # Compile data
    data = fields.to_data(trial_tstamps)
    return data


if __name__ == "__main__":
    main()

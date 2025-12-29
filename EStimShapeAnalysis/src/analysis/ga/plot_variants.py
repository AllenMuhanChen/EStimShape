from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import create_branch, create_pipeline
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from clat.util.connection import Connection
import pandas as pd


def main():
    analysis = PlotIncludedVariants()
    compiled_data = analysis.compile()
    session_id = "251226_0"
    channel = "A-025"
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class PlotIncludedVariants(PlotTopNAnalysis):
    def analyze(self, channel, compiled_data=None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        compiled_data = compiled_data[compiled_data[self.spike_rates_col].notna()]
        compiled_data['Spike Rate'] = compiled_data[self.spike_rates_col].apply(
            lambda x: x[channel] if channel in x else 0)

        # Get included variants from database
        included_stim_ids = self._get_included_variants_from_db()

        if not included_stim_ids:
            print("No included variants found in IncludedVariants table!")
            return

        print(f"Found {len(included_stim_ids)} included variants in database")

        # Filter compiled_data to only include these variants
        included_data = compiled_data[
            compiled_data['StimSpecId'].isin(included_stim_ids)
        ].copy()

        if included_data.empty:
            print("No matching data found for included variants!")
            return

        # Calculate average response and rank
        avg_response = included_data.groupby('StimSpecId')['Spike Rate'].mean().reset_index()
        avg_response.rename(columns={'Spike Rate': 'Avg Response Rate'}, inplace=True)
        avg_response['Rank'] = avg_response['Avg Response Rate'].rank(
            ascending=False, method='first')

        # Merge ranks back
        included_data = included_data.merge(
            avg_response[['StimSpecId', 'Rank']],
            on='StimSpecId',
            how='left'
        )

        print(f"Plotting {len(included_data)} included variant presentations")

        # Create visualization - single row, sorted by rank
        visualize_module = create_grouped_stimuli_module(
            cell_size=(200, 200),
            response_rate_col=self.spike_rates_col,
            response_rate_key=channel,
            path_col='ThumbnailPath',
            col_col='Rank',
            save_path=f"{self.save_path}/{channel}_included_variants.png",
            module_name="Included_Variants",
            publish_mode=False,
        )

        visualize_branch = create_branch().then(visualize_module)
        pipeline = create_pipeline().make_branch(visualize_branch).build()
        result = pipeline.run(included_data)

        plt.show()

    def _get_included_variants_from_db(self):
        """Get non-excluded variant IDs from IncludedVariants table."""
        try:
            conn = Connection(context.ga_database)

            # Query for non-excluded variants
            query_sql = "SELECT stim_id FROM IncludedVariants WHERE manually_excluded = FALSE"
            conn.execute(query_sql)

            results = conn.fetch_all()

            if not results:
                print("No non-excluded variants found in IncludedVariants table")
                return []

            # Extract stim_ids from results (each result is a tuple)
            stim_ids = [int(row[0]) for row in results]

            return stim_ids

        except Exception as e:
            print(f"Error reading from IncludedVariants table: {e}")
            return []


if __name__ == "__main__":
    main()
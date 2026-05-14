from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import create_branch, create_pipeline
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.response_spec import ResponseSpec
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from clat.util.connection import Connection
import pandas as pd


def main():
    analysis = PlotIncludedVariants()
    compiled_data = analysis.compile()
    session_id = "260421_0"
    channel = "GA"
    data_type = "GA" if channel == "GA" else "raw"
    analysis.run(session_id, data_type, channel, compiled_data=compiled_data)


class PlotIncludedVariants(PlotTopNAnalysis):
    def analyze(self, channel, compiled_data=None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        spec = ResponseSpec(channel, use_baseline_correction=self.use_baseline_correction)
        try:
            prepared = spec.apply(compiled_data, spike_rates_col=self.spike_rates_col)
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        compiled_data = prepared.data
        response_col = prepared.response_col

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
        avg_response = included_data.groupby('StimSpecId')[response_col].mean().reset_index()
        avg_response.rename(columns={response_col: 'Avg Response Rate'}, inplace=True)
        avg_response['Rank'] = avg_response['Avg Response Rate'].rank(
            ascending=False, method='first')

        # Merge ranks back
        included_data = included_data.merge(
            avg_response[['StimSpecId', 'Rank']],
            on='StimSpecId',
            how='left'
        )

        print(f"Plotting {len(included_data)} included variant presentations")

        viz_kwargs = dict(
            cell_size=(200, 200),
            response_rate_col=response_col,
            path_col='ThumbnailPath',
            col_col='Rank',
            save_path=f"{self.save_path}/{prepared.channel_label}{prepared.baseline_suffix}_included_variants.png",
            module_name="Included_Variants",
            publish_mode=False,
        )
        if prepared.response_key is not None:
            viz_kwargs['response_rate_key'] = prepared.response_key
        visualize_module = create_grouped_stimuli_module(**viz_kwargs)

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
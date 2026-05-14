from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import create_branch, create_pipeline
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.response_spec import ResponseSpec
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.pga.estim_phase import has_preservation_history
from src.pga.stim_types import StimType
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from clat.util.connection import Connection
import pandas as pd


def main():
    channel = "GA"  # "GA", "Cluster", a single channel name, or a list of channel names
    analysis = PlotVariants(save_included_variants=False)
    compiled_data = None
    # compiled_data = analysis.compile_and_export()
    session_id = "260512_0"
    data_type = "GA" if channel == "GA" else "raw"
    analysis.run(session_id, data_type, channel, compiled_data=compiled_data)


class PlotVariants(PlotTopNAnalysis):
    threshold = 0.75

    def __init__(self, save_included_variants=False, use_baseline_correction=False):
        super().__init__(use_baseline_correction=use_baseline_correction)
        self.save_included_variants = save_included_variants

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

        # Find lineages with more than 10 stimuli
        lineage_counts = compiled_data['Lineage'].value_counts()
        top_lineages = lineage_counts[lineage_counts > 10].index
        print(f"Top {len(top_lineages)} lineages: {top_lineages.tolist()}")

        # Filter for variants only
        variants_data = self.filter_for_variants(compiled_data)

        # Calculate average response rate and rank for variants
        avg_response = variants_data.groupby(['GenId', 'StimSpecId', 'Lineage'])[response_col].mean().reset_index()
        avg_response.rename(columns={response_col: 'Avg Response Rate'}, inplace=True)
        avg_response['Rank'] = avg_response.groupby('Lineage')['Avg Response Rate'].rank(
            ascending=False, method='first')

        # Merge ranks back
        variants_data = variants_data.merge(
            avg_response[['GenId', 'StimSpecId', 'Lineage', 'Rank']],
            on=['GenId', 'StimSpecId', 'Lineage'],
            how='left'
        )
        variants_data['RowType'] = 'Variant'

        # DEBUG: Check parent IDs
        print("\n=== DEBUG PARENT LOOKUP ===")
        parent_ids = variants_data['ParentId'].unique()
        print(f"Number of unique ParentIds in variants: {len(parent_ids)}")
        print(f"Sample ParentIds: {parent_ids[:5]}")

        matching_parents = compiled_data[compiled_data['StimSpecId'].isin(parent_ids)]
        print(f"Number of matching parents found in compiled_data: {len(matching_parents)}")
        if matching_parents.empty:
            print("\nChecking why no parents found...")
            print(f"Sample StimSpecIds in compiled_data: {compiled_data['StimSpecId'].head(10).tolist()}")
            print(f"StimTypes in compiled_data: {compiled_data['StimType'].unique()}")

        # Get parent information for each variant
        parent_rows = []
        parents_data = compiled_data[compiled_data['StimSpecId'].isin(parent_ids)].copy()
        for _, variant in variants_data.iterrows():
            parent_id = variant['ParentId']
            matching_parents = parents_data[parents_data['StimSpecId'] == parent_id]
            if not matching_parents.empty:
                parent_row = matching_parents.iloc[0].copy()
                parent_row['Rank'] = variant['Rank']
                parent_row['Lineage'] = variant['Lineage']
                parent_row['RowType'] = 'Parent'
                parent_rows.append(parent_row)

        if parent_rows:
            parents_df = pd.DataFrame(parent_rows)
            plot_data = pd.concat([variants_data, parents_df], ignore_index=True)
            print(f"Successfully created plot_data with {len(variants_data)} variants and {len(parents_df)} parents")
        else:
            print("No parent data found - plotting variants only")
            plot_data = variants_data

        visualize_params = {
            'cell_size': (200, 200),
            'response_rate_col': response_col,
            'path_col': 'ThumbnailPath',
            'row_col': 'RowType',
            'col_col': 'Rank',
            'subgroup_col': 'Lineage',
            'filter_values': {"Lineage": top_lineages.tolist()},
            'save_path': f"{self.save_path}/{prepared.channel_label}{prepared.baseline_suffix}_variants_with_parents.png",
            'module_name': "Variants_With_Parents",
            'publish_mode': False,
            'border_width': 50,
        }
        if prepared.response_key is not None:
            visualize_params['response_rate_key'] = prepared.response_key

        visualize_module = create_grouped_stimuli_module(**visualize_params)
        visualize_branch = create_branch().then(visualize_module)
        pipeline = create_pipeline().make_branch(visualize_branch).build()
        result = pipeline.run(plot_data)

        if self.save_included_variants:
            self._save_included_variants_to_db(compiled_data, response_col)

        plt.show()

    def filter_for_variants(self, compiled_data):
        variants_data = compiled_data[
            compiled_data['StimType'].isin([StimType.REGIME_ESTIM_VARIANTS.value, StimType.REGIME_ESTIM_DELTA.value])]
        return variants_data

    def _save_included_variants_to_db(self, compiled_data, response_col):
        """Save included variants to the GA database."""
        try:
            conn = Connection(context.ga_database)

            # Manual exclusions
            manual_exclusions = []

            # Create table
            create_table_sql = """
                               CREATE TABLE IF NOT EXISTS IncludedVariants \
                               ( \
                                   stim_id           BIGINT PRIMARY KEY, \
                                   response          DOUBLE, \
                                   threshold_used    DOUBLE, \
                                   manually_excluded BOOLEAN   DEFAULT FALSE, \
                                   exclusion_reason  VARCHAR(255), \
                                   date_added        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                               ) \
                               """
            conn.execute(create_table_sql)
            print("\n=== DATABASE SAVING ===")
            print("Ensured IncludedVariants table exists")

            # Clear existing
            conn.execute("DELETE FROM IncludedVariants")
            print("Cleared existing IncludedVariants entries")

            # Filter for variants
            variants = self.filter_for_variants(compiled_data)

            if variants.empty:
                print("No variants found to save")
                return

            # Group by StimSpecId and get mean response (deduplicate)
            variants_grouped = variants.groupby('StimSpecId')[response_col].mean().reset_index()

            # Calculate threshold (60% of max)
            max_response = variants_grouped[response_col].max()
            threshold = self.threshold * max_response
            print(f"Max response: {max_response:.2f}, Threshold (60%): {threshold:.2f}")

            # Filter by threshold
            included = variants_grouped[variants_grouped[response_col] >= threshold]

            print(f"Found {len(included)} variants above threshold")

            # Insert
            insert_sql = """
                         INSERT INTO IncludedVariants
                         (stim_id, response, threshold_used, manually_excluded, exclusion_reason)
                         VALUES (%s, %s, %s, %s, %s) \
                         """

            for _, row in included.iterrows():
                stim_id = int(row['StimSpecId'])
                excluded = stim_id in manual_exclusions
                exclusion_reason = "Manually excluded via analysis script" if excluded else None

                conn.execute(insert_sql, (
                    stim_id,
                    float(row[response_col]),
                    threshold,
                    excluded,
                    exclusion_reason
                ))

            print(f"Saved {len(included)} variants to IncludedVariants table")

            excluded_count = sum(1 for _, row in included.iterrows()
                                 if int(row['StimSpecId']) in manual_exclusions)
            if excluded_count > 0:
                print(f"Marked {excluded_count} variants as manually excluded")

        except Exception as e:
            print(f"Warning: Could not save to database: {e}")


if __name__ == "__main__":
    main()
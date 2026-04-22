from matplotlib import pyplot as plt
from clat.pipeline.pipeline_base_classes import create_branch, create_pipeline
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.pga.stim_types import StimType
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from clat.util.connection import Connection
import pandas as pd


def main():
    analysis = PlotVariantDeltas(
        use_ga_response=False,
        to_save_to_db=False,
        threshold=0.5,
        plot_included_only=False)
    compiled_data = None  # Set to None to import from repository
    # compiled_data = analysis.compile_and_export()
    session_id = "260421_0"
    channel = "A-028"
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class PlotVariantDeltas(PlotTopNAnalysis):
    def __init__(self, use_ga_response=True, to_save_to_db=False, threshold=0.5, plot_included_only=True):
        super().__init__()
        self.use_ga_response = use_ga_response
        self.to_save_to_db = to_save_to_db
        self.threshold = threshold
        self.plot_included_only = plot_included_only

    def analyze(self, channel, compiled_data=None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        # Setup response column
        if self.use_ga_response:
            if 'GA Response' not in compiled_data.columns:
                print("Error: 'GA Response' column not found in data!")
                print(f"Available columns: {compiled_data.columns.tolist()}")
                return
            compiled_data = compiled_data[compiled_data['GA Response'].notna()]
            response_col_name = 'GA Response'
            response_key = None
            print("Using GA Response (not channel-specific)")
        else:
            compiled_data = compiled_data[compiled_data[self.spike_rates_col].notna()]
            compiled_data['Spike Rate'] = compiled_data[self.spike_rates_col].apply(
                lambda x: x[channel] if channel in x else 0)
            response_col_name = 'Spike Rate'
            response_key = channel
            print(f"Using channel-specific spike rates for {channel}")

        # Get included variants from database
        included_variant_ids = self._get_included_variants_from_db()
        if not included_variant_ids:
            print("No included variants found in IncludedVariants table!")
            return
        print(f"Found {len(included_variant_ids)} included variants")

        # Only DELTA-type stims are candidates to be the "delta" in a pair,
        # preventing variant/variant pairs from forming.
        deltas_data = compiled_data[compiled_data['StimType'] == StimType.REGIME_ESTIM_DELTA.value].copy()
        if deltas_data.empty:
            print("No REGIME_ESTIM_DELTA stimuli found!")
            return

        # Build lookup used both during pair-building and the lineage filter
        stim_info = compiled_data.drop_duplicates('StimSpecId').set_index('StimSpecId')[['StimType', 'ParentId']]

        # Build valid (delta, paired_variant) pairs
        pair_records = []
        for _, row in compiled_data.iterrows():
            parent_id = row['ParentId']
            stim_id = row['StimSpecId']

            if parent_id in included_variant_ids and stim_id in deltas_data['StimSpecId'].values:
                # Normal: included variant is parent, delta child
                pair_records.append({'StimSpecId': stim_id, 'PairedVariantId': parent_id})
            elif stim_id in included_variant_ids:
                # Reversed: stim IS the included variant, parent may be the delta
                if parent_id in included_variant_ids:
                    continue  # variant→variant, skip
                # Only accept parent as delta if it is actually DELTA type
                if parent_id not in stim_info.index:
                    continue
                if stim_info.loc[parent_id, 'StimType'] != StimType.REGIME_ESTIM_DELTA.value:
                    continue
                parent_row = compiled_data[compiled_data['StimSpecId'] == parent_id]
                if not parent_row.empty:
                    if parent_id not in deltas_data['StimSpecId'].values:
                        deltas_data = pd.concat([deltas_data, parent_row], ignore_index=True)
                    pair_records.append({'StimSpecId': parent_id, 'PairedVariantId': stim_id})
                else:
                    print(f"Warning: Parent ID {parent_id} of included variant {stim_id} not found in compiled data!")

        if not pair_records:
            print("No valid delta-variant pairs found!")
            return

        paired_delta_ids = {r['StimSpecId'] for r in pair_records}
        deltas_data = deltas_data[deltas_data['StimSpecId'].isin(paired_delta_ids)].copy()
        pair_map = pd.DataFrame(pair_records).drop_duplicates()

        print(f"Found {len(pair_map)} delta-variant pairs")

        # Average response per (delta, paired_variant)
        deltas_merged = deltas_data.merge(pair_map, on='StimSpecId', how='inner')
        delta_avg_response = deltas_merged.groupby(['StimSpecId', 'PairedVariantId'])[
            response_col_name].mean().reset_index()
        delta_avg_response.rename(columns={response_col_name: 'Delta Response'}, inplace=True)

        variant_responses = self._get_variant_responses(compiled_data, included_variant_ids, channel)
        delta_avg_response = delta_avg_response.merge(
            variant_responses[['StimSpecId', 'Response']],
            left_on='PairedVariantId',
            right_on='StimSpecId',
            how='left',
            suffixes=('', '_variant')
        )
        delta_avg_response.rename(columns={'Response': 'Variant Response'}, inplace=True)
        delta_avg_response.drop('StimSpecId_variant', axis=1, inplace=True)

        delta_avg_response['Ratio'] = delta_avg_response['Delta Response'] / delta_avg_response['Variant Response']
        delta_avg_response['Included'] = delta_avg_response['Ratio'] < self.threshold

        # Drop pairs where a DELTA-type stim acts as the "variant" but isn't the child of the true delta
        rows_to_drop = []
        for idx, row in delta_avg_response.iterrows():
            variant_id = row['PairedVariantId']
            delta_id = row['StimSpecId']
            if variant_id not in stim_info.index:
                continue
            if stim_info.loc[variant_id, 'StimType'] == StimType.REGIME_ESTIM_DELTA.value:
                if stim_info.loc[variant_id, 'ParentId'] != delta_id:
                    rows_to_drop.append(idx)
                    print(f"  Dropped pair: DELTA {variant_id} acting as variant is not child of {delta_id}")
        delta_avg_response = delta_avg_response.drop(rows_to_drop).reset_index(drop=True)

        print(f"Valid pairs after lineage filter: {len(delta_avg_response)}")
        print(f"  Included (ratio < {self.threshold}): {delta_avg_response['Included'].sum()}")
        print(f"  Excluded: {(~delta_avg_response['Included']).sum()}")

        # Decide which pairs go into the plot
        if self.plot_included_only:
            plot_subset = delta_avg_response[delta_avg_response['Included']].copy()
        else:
            plot_subset = delta_avg_response.copy()

        if plot_subset.empty:
            print("No pairs to plot!")
            return

        plot_subset['Rank'] = plot_subset['Delta Response'].rank(ascending=False, method='first')

        # Build delta rows for plot
        plot_delta_ids = plot_subset['StimSpecId'].unique()
        deltas_plot_data = compiled_data[compiled_data['StimSpecId'].isin(plot_delta_ids)].copy()
        deltas_plot_data = deltas_plot_data.groupby(['StimSpecId', 'ParentId']).agg({
            'GenId': 'first',
            'Lineage': 'first',
            response_col_name: 'mean',
            'ThumbnailPath': 'first',
            'StimType': 'first'
        }).reset_index()
        deltas_plot_data = plot_subset[['StimSpecId', 'Rank']].merge(
            deltas_plot_data, on='StimSpecId', how='outer'
        )
        if self.use_ga_response:
            deltas_plot_data = deltas_plot_data.drop_duplicates(subset=['StimSpecId', 'Rank'], keep='first')
        deltas_plot_data['RowType'] = 'Delta'

        # Build variant rows for plot
        paired_variant_ids = plot_subset['PairedVariantId'].unique()
        paired_variants_data = compiled_data[compiled_data['StimSpecId'].isin(paired_variant_ids)].copy()

        paired_variant_rows = []
        for _, delta_row in plot_subset.iterrows():
            parent_id = delta_row['PairedVariantId']
            rank = delta_row['Rank']
            matching_parents = paired_variants_data[paired_variants_data['StimSpecId'] == parent_id]
            if not matching_parents.empty:
                if self.use_ga_response:
                    parent_row = matching_parents.iloc[0].copy()
                    parent_row['Rank'] = rank
                    parent_row['RowType'] = 'Variant'
                    paired_variant_rows.append(parent_row)
                else:
                    for _, parent_row in matching_parents.iterrows():
                        parent_row_copy = parent_row.copy()
                        parent_row_copy['Rank'] = rank
                        parent_row_copy['RowType'] = 'Variant'
                        paired_variant_rows.append(parent_row_copy)

        if paired_variant_rows:
            paired_variant_df = pd.DataFrame(paired_variant_rows)
            plot_data = pd.concat([deltas_plot_data, paired_variant_df], ignore_index=True)
            print(f"Plotting {len(deltas_plot_data)} deltas and {len(paired_variant_df)} variants")
        else:
            print("No parent data found")
            plot_data = deltas_plot_data

        if self.plot_included_only:
            title = 'Included Deltas with Paired Variants'
        else:
            title = 'All Delta-Variant Pairs'

        save_path = f"{self.save_path}/{channel}_delta_variant_pairs.png"
        visualize_params = {
            'cell_size': (200, 200),
            'response_rate_col': response_col_name,
            'path_col': 'ThumbnailPath',
            'row_col': 'RowType',
            'col_col': 'Rank',
            'save_path': save_path,
            'module_name': "Deltas_With_Paired_Variants",
            'cols_in_info_box': ['StimType', "StimSpecId", "Response", "ParentId"],
            'publish_mode': False,
            'title': title,
            'border_width': 50,
        }

        if not self.use_ga_response:
            visualize_params['response_rate_key'] = response_key

        visualize_module = create_grouped_stimuli_module(**visualize_params)
        visualize_branch = create_branch().then(visualize_module)
        pipeline = create_pipeline().make_branch(visualize_branch).build()
        pipeline.run(plot_data)
        plt.show()

        if self.to_save_to_db:
            self._save_deltas_to_db(delta_avg_response)

    def _get_included_variants_from_db(self):
        """Get non-excluded variant IDs from IncludedVariants table."""
        try:
            conn = Connection(context.ga_database)

            query_sql = "SELECT stim_id FROM IncludedVariants WHERE manually_excluded = FALSE"
            conn.execute(query_sql)

            results = conn.fetch_all()

            if not results:
                return []

            stim_ids = [int(row[0]) for row in results]
            return stim_ids

        except Exception as e:
            print(f"Error reading from IncludedVariants table: {e}")
            return []

    def _get_variant_responses(self, compiled_data, variant_ids, channel):
        """Get variant responses from IncludedVariants table."""
        try:
            conn = Connection(context.ga_database)

            query_sql = "SELECT stim_id, response FROM IncludedVariants WHERE manually_excluded = FALSE"
            conn.execute(query_sql)

            results = conn.fetch_all()

            if results:
                variant_responses = pd.DataFrame(results, columns=['StimSpecId', 'Response'])
                return variant_responses

        except Exception as e:
            print(f"Could not read from IncludedVariants, calculating from data: {e}")

        # Fallback: calculate from compiled_data using appropriate column
        variants_data = compiled_data[compiled_data['StimSpecId'].isin(variant_ids)].copy()
        response_col_name = 'GA Response' if self.use_ga_response else 'Spike Rate'
        variant_responses = variants_data.groupby('StimSpecId')[response_col_name].mean().reset_index()
        variant_responses.rename(columns={response_col_name: 'Response'}, inplace=True)
        return variant_responses

    def _read_deltas_from_db(self):
        """Read delta information from IncludedDeltas table."""
        try:
            conn = Connection(context.ga_database)

            query_sql = """
                        SELECT delta_id, variant_id, response_delta, response_variant, ratio, included
                        FROM IncludedDeltas \
                        """
            conn.execute(query_sql)
            results = conn.fetch_all()

            if not results:
                return None

            # Convert to DataFrame
            delta_data = pd.DataFrame(results, columns=[
                'StimSpecId', 'PairedVariantId', 'Delta Response',
                'Variant Response', 'Ratio', 'Included'
            ])

            # Convert data types (DB returns everything as objects/integers)
            delta_data['StimSpecId'] = delta_data['StimSpecId'].astype(int)
            delta_data['PairedVariantId'] = delta_data['PairedVariantId'].astype(int)
            delta_data['Delta Response'] = delta_data['Delta Response'].astype(float)
            delta_data['Variant Response'] = delta_data['Variant Response'].astype(float)
            delta_data['Ratio'] = delta_data['Ratio'].astype(float)
            delta_data['Included'] = delta_data['Included'].astype(bool)

            return delta_data

        except Exception as e:
            print(f"Error reading from IncludedDeltas table: {e}")
            return None

    def _save_deltas_to_db(self, delta_data):
        """Save delta information to IncludedDeltas table."""
        try:
            conn = Connection(context.ga_database)

            # Create table
            create_table_sql = """
                               CREATE TABLE IF NOT EXISTS IncludedDeltas \
                               ( \
                                   delta_id         BIGINT PRIMARY KEY, \
                                   variant_id       BIGINT, \
                                   response_delta   DOUBLE, \
                                   response_variant DOUBLE, \
                                   ratio            DOUBLE, \
                                   included         BOOLEAN, \
                                   date_added       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                               ) \
                               """
            conn.execute(create_table_sql)
            print("\n=== DATABASE SAVING ===")
            print("Ensured IncludedDeltas table exists")

            # Check if data already exists
            conn.execute("SELECT COUNT(*) FROM IncludedDeltas")
            existing_count = conn.fetch_one()

            if existing_count > 0:
                print(f"\nWARNING: IncludedDeltas table already contains {existing_count} entries!")
                response = input("Do you want to DELETE all existing data and replace it? (yes/no): ").strip().lower()

                if response not in ['yes', 'y']:
                    print("Operation cancelled. No changes made to database.")
                    return

                print("User confirmed: proceeding with deletion and replacement...")

            # Clear existing
            conn.execute("DELETE FROM IncludedDeltas")
            if existing_count > 0:
                print(f"Deleted {existing_count} existing IncludedDeltas entries")

            # Insert
            insert_sql = """
                         INSERT INTO IncludedDeltas
                         (delta_id, variant_id, response_delta, response_variant, ratio, included)
                         VALUES (%s, %s, %s, %s, %s, %s) \
                         """

            for _, row in delta_data.iterrows():
                conn.execute(insert_sql, (
                    int(row['StimSpecId']),
                    int(row['PairedVariantId']),
                    float(row['Delta Response']),
                    float(row['Variant Response']),
                    float(row['Ratio']),
                    bool(row['Included'])
                ))

            print(f"Saved {len(delta_data)} deltas to IncludedDeltas table")
            print(f"  Included: {delta_data['Included'].sum()}")
            print(f"  Excluded: {(~delta_data['Included']).sum()}")

        except Exception as e:
            print(f"Warning: Could not save to database: {e}")


if __name__ == "__main__":
    main()
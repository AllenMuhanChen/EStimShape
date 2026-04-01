from matplotlib import pyplot as plt
from clat.pipeline.pipeline_base_classes import create_branch, create_pipeline
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from clat.util.connection import Connection
import pandas as pd


def main():
    analysis = PlotVariantDeltas(
        use_ga_response=True,# Set to False to use channel-specific spike rates
        to_save_to_db=False)
    compiled_data = None  # Set to None to import from repository
    # compiled_data = analysis.compile()
    session_id = "260331_0"
    channel = "GA"
    analysis.run(session_id, "GA", channel, compiled_data=compiled_data)


class PlotVariantDeltas(PlotTopNAnalysis):
    def __init__(self, use_ga_response=True, to_save_to_db=False):
        """
        Initialize PlotVariantDeltas analysis.

        Args:
            use_ga_response: If True, use 'GA Response' column. If False, use channel-specific spike rates.
            to_save_to_db: If True, calculate and save to database. If False, read from existing database.
        """
        super().__init__()
        self.use_ga_response = use_ga_response
        self.to_save_to_db = to_save_to_db

    def analyze(self, channel, compiled_data=None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        # Setup response column based on mode
        if self.use_ga_response:
            if 'GA Response' not in compiled_data.columns:
                print("Error: 'GA Response' column not found in data!")
                print(f"Available columns: {compiled_data.columns.tolist()}")
                return

            compiled_data = compiled_data[compiled_data['GA Response'].notna()]
            response_col = 'GA Response'
            response_key = None
            print(f"Using GA Response (not channel-specific)")
        else:
            compiled_data = compiled_data[compiled_data[self.spike_rates_col].notna()]
            compiled_data['Spike Rate'] = compiled_data[self.spike_rates_col].apply(
                lambda x: x[channel] if channel in x else 0)
            response_col = self.spike_rates_col
            response_key = channel
            print(f"Using channel-specific spike rates for {channel}")

        # Two modes: calculate and save, or read from existing table
        if self.to_save_to_db:
            # CALCULATION MODE: Compute delta responses and save to database
            print("\n=== CALCULATION MODE ===")
            print("Computing delta responses and saving to database...")

            # Get included variants from database
            included_variant_ids = self._get_included_variants_from_db()

            if not included_variant_ids:
                print("No included variants found in IncludedVariants table!")
                return

            print(f"Found {len(included_variant_ids)} included variants")

            # Filter for delta stimuli
            deltas_data = compiled_data[compiled_data['StimType'] == "REGIME_ESTIM_DELTA"].copy()

            if deltas_data.empty:
                print("No REGIME_ESTIM_DELTA stimuli found!")
                return

            # Filter deltas to only those whose parent is an included variant
            deltas_data = deltas_data[deltas_data['ParentId'].isin(included_variant_ids)].copy()

            if deltas_data.empty:
                print("No deltas found with parents in IncludedVariants!")
                return

            print(f"Found {len(deltas_data)} delta presentations with included variant parents")

            # Calculate average response for each delta using appropriate column
            response_col_name = 'GA Response' if self.use_ga_response else 'Spike Rate'
            delta_avg_response = deltas_data.groupby(['StimSpecId', 'ParentId'])[response_col_name].mean().reset_index()
            delta_avg_response.rename(columns={response_col_name: 'Delta Response'}, inplace=True)

            # Get variant responses
            variant_responses = self._get_variant_responses(compiled_data, included_variant_ids, channel)

            # Merge variant responses
            delta_avg_response = delta_avg_response.merge(
                variant_responses[['StimSpecId', 'Response']],
                left_on='ParentId',
                right_on='StimSpecId',
                how='left',
                suffixes=('', '_variant')
            )
            delta_avg_response.rename(columns={'Response': 'Variant Response'}, inplace=True)
            delta_avg_response.drop('StimSpecId_variant', axis=1, inplace=True)

            # Calculate ratio and determine inclusion
            delta_avg_response['Ratio'] = delta_avg_response['Delta Response'] / delta_avg_response['Variant Response']
            delta_avg_response['Included'] = delta_avg_response['Ratio'] < 0.5

            print(
                f"Delta inclusion: {delta_avg_response['Included'].sum()} included, {(~delta_avg_response['Included']).sum()} excluded")

            # Save to database
            self._save_deltas_to_db(delta_avg_response)

        else:
            # READ MODE: Load existing delta-variant pairs from database
            print("\n=== READ MODE ===")
            print("Reading delta-variant pairs from existing IncludedDeltas table...")

            delta_avg_response = self._read_deltas_from_db()

            if delta_avg_response is None or delta_avg_response.empty:
                print("ERROR: No data found in IncludedDeltas table!")
                print("Please run with to_save_to_db=True first to populate the table.")
                return

            print(f"Loaded {len(delta_avg_response)} delta entries from database")
            print(
                f"Delta inclusion: {delta_avg_response['Included'].sum()} included, {(~delta_avg_response['Included']).sum()} excluded")

        # Prepare data for visualization - filter for included deltas only
        included_deltas = delta_avg_response[delta_avg_response['Included']].copy()

        if included_deltas.empty:
            print("No deltas meet inclusion criteria (ratio < 0.5)")
            return

        # Rank by delta response
        included_deltas['Rank'] = included_deltas['Delta Response'].rank(ascending=False, method='first')

        # Merge rank back to full deltas_data - need to get deltas_data from compiled_data
        deltas_data = compiled_data[compiled_data['StimType'] == "REGIME_ESTIM_DELTA"].copy()
        deltas_data = deltas_data.merge(
            included_deltas[['StimSpecId', 'Rank']],
            on='StimSpecId',
            how='inner'
        )

        # If using GA Response, only keep one row per StimSpecId (since GA Response is already a summary)
        # If using spike rates, keep all presentations for proper averaging
        if self.use_ga_response:
            deltas_data = deltas_data.drop_duplicates(subset=['StimSpecId', 'Rank'], keep='first')

        deltas_data['RowType'] = 'Delta'

        # Get parent data
        parent_ids = included_deltas['ParentId'].unique()
        parents_data = compiled_data[compiled_data['StimSpecId'].isin(parent_ids)].copy()

        # For each delta, add corresponding parent presentations at same rank
        parent_rows = []
        for _, delta_row in included_deltas.iterrows():
            parent_id = delta_row['ParentId']
            rank = delta_row['Rank']

            matching_parents = parents_data[parents_data['StimSpecId'] == parent_id]

            if not matching_parents.empty:
                if self.use_ga_response:
                    # GA Response: only need one row (it's already a summary value)
                    parent_row = matching_parents.iloc[0].copy()
                    parent_row['Rank'] = rank
                    parent_row['RowType'] = 'Parent'
                    parent_rows.append(parent_row)
                else:
                    # Spike rates: need ALL presentations for proper averaging
                    for _, parent_row in matching_parents.iterrows():
                        parent_row_copy = parent_row.copy()
                        parent_row_copy['Rank'] = rank
                        parent_row_copy['RowType'] = 'Parent'
                        parent_rows.append(parent_row_copy)

        if parent_rows:
            parents_df = pd.DataFrame(parent_rows)
            plot_data = pd.concat([deltas_data, parents_df], ignore_index=True)
            print(f"Plotting {len(deltas_data)} deltas and {len(parents_df)} parents")
        else:
            print("No parent data found")
            plot_data = deltas_data
        if self.to_save_to_db:
            save_path = f"{self.save_path}/{channel}_calculated_deltas_with_parents.png"
        else:
            save_path = f"{self.save_path}/{channel}_included_deltas_with_parents.png"
        # Create visualization
        visualize_params = {
            'cell_size': (200, 200),
            'response_rate_col': response_col,
            'path_col': 'ThumbnailPath',
            'row_col': 'RowType',
            'col_col': 'Rank',
            'save_path': save_path,
            'module_name': "Deltas_With_Parents",
            'publish_mode': False,
            'title': 'Calculated Variants and Deltas' if self.to_save_to_db else 'Tested Variants and Deltas',
            'border_width': 50,
        }

        # Add response_rate_key only if using channel-specific mode
        if not self.use_ga_response:
            visualize_params['response_rate_key'] = response_key

        visualize_module = create_grouped_stimuli_module(**visualize_params)

        visualize_branch = create_branch().then(visualize_module)
        pipeline = create_pipeline().make_branch(visualize_branch).build()
        result = pipeline.run(plot_data)

        plt.show()

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
                'StimSpecId', 'ParentId', 'Delta Response',
                'Variant Response', 'Ratio', 'Included'
            ])

            # Convert data types (DB returns everything as objects/integers)
            delta_data['StimSpecId'] = delta_data['StimSpecId'].astype(int)
            delta_data['ParentId'] = delta_data['ParentId'].astype(int)
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
                    int(row['ParentId']),
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
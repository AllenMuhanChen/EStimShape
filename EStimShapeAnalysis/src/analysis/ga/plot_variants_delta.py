from matplotlib import pyplot as plt
from clat.pipeline.pipeline_base_classes import create_branch, create_pipeline
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.response_spec import ResponseSpec
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.pga.stim_types import StimType
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context
from clat.util.connection import Connection
import pandas as pd

# Plot mode constants
PLOT_MODE_ALL = 'all'            # Compute pairs and show all, even those not passing thresholds
PLOT_MODE_PASSING = 'passing'    # Compute pairs and show only those passing thresholds
PLOT_MODE_DB_INCLUDED = 'db_included'  # Show exactly the stims with included=1 in DB, no threshold logic


def main():

    channel = "A-006"  # "GA" for GA Response, "Cluster" for current cluster, single channel name, or list
    use_baseline_correction = False

    analysis = PlotVariantDeltas(
        to_save_to_db=True,
        delta_threshold=0.6,
        variant_threshold=0.4,
        plot_mode=PLOT_MODE_PASSING,
        use_baseline_correction=use_baseline_correction,)
    compiled_data = None  # Set to None to import from repository
    # compiled_data = analysis.compile_and_export()
    data_type = "GA" if channel == "GA" else "raw"
    (session_id, _) = read_session_id_and_date_from_db_name(context.ga_database)
    analysis.run(session_id, data_type, channel, compiled_data=compiled_data)


class PlotVariantDeltas(PlotTopNAnalysis):
    def __init__(self, to_save_to_db=False, delta_threshold=0.5,
                 plot_mode=PLOT_MODE_PASSING, variant_threshold=0.75,
                 use_baseline_correction=False):
        super().__init__(use_baseline_correction=use_baseline_correction)
        self.to_save_to_db = to_save_to_db
        self.threshold = delta_threshold
        self.plot_mode = plot_mode
        self.variant_threshold = variant_threshold
        # Set by analyze() from the channel arg; internal helpers read this
        # to switch between per-stim (GA) and per-trial (channel) dedup logic.
        self.use_ga_response: bool = False

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
        self.use_ga_response = spec.use_ga_response
        compiled_data = prepared.data
        channel = prepared.channel
        channel_label = prepared.channel_label
        response_col_name = prepared.response_col
        response_key = prepared.response_key

        if self.plot_mode == PLOT_MODE_DB_INCLUDED:
            plot_data, title = self._build_plot_data_from_db(compiled_data, response_col_name)
            if plot_data is None:
                return
            delta_avg_response = None
        else:
            plot_data, title, delta_avg_response = self._build_plot_data_from_calculations(
                compiled_data, response_col_name)
            if plot_data is None:
                return

        save_path = f"{self.save_path}/{channel_label}{prepared.baseline_suffix}_delta_variant_pairs.png"
        visualize_params = {
            'cell_size': (200, 200),
            'response_rate_col': response_col_name,
            'path_col': 'ThumbnailPath',
            'row_col': 'RowType',
            'col_col': 'Rank',
            'save_path': save_path,
            'module_name': "Deltas_With_Paired_Variants",
            'cols_in_info_box': ['StimType', "StimSpecId", "Response", "ParentId", 'GA Response'],
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

        if self.to_save_to_db and delta_avg_response is not None:
            self._save_deltas_to_db(delta_avg_response)

    def _build_plot_data_from_db(self, compiled_data, response_col_name):
        """Build plot data using included=1 pairs from DB; responses come from compiled_data (current channel)."""
        db_data = self._read_deltas_from_db()
        if db_data is None or db_data.empty:
            print("No data found in IncludedDeltas database table!")
            return None, None

        included_pairs = db_data[db_data['Included']].copy()
        if included_pairs.empty:
            print("No pairs with included=1 found in database!")
            return None, None

        print(f"Found {len(included_pairs)} DB-included pairs")
        included_pairs['Rank'] = included_pairs['Ratio'].rank(ascending=True, method='first')

        delta_ids = included_pairs['StimSpecId'].unique()
        deltas_raw = compiled_data[compiled_data['StimSpecId'].isin(delta_ids)].copy()
        deltas_plot_data = included_pairs[['StimSpecId', 'Rank']].merge(
            deltas_raw, on='StimSpecId', how='inner'
        )
        if self.use_ga_response:
            deltas_plot_data = deltas_plot_data.drop_duplicates(subset=['StimSpecId', 'Rank'], keep='first')
        deltas_plot_data['RowType'] = 'Delta'

        variant_ids = included_pairs['PairedVariantId'].unique()
        paired_variants_data = compiled_data[compiled_data['StimSpecId'].isin(variant_ids)].copy()

        paired_variant_rows = []
        for _, pair_row in included_pairs.iterrows():
            variant_id = pair_row['PairedVariantId']
            rank = pair_row['Rank']
            matching = paired_variants_data[paired_variants_data['StimSpecId'] == variant_id]
            if not matching.empty:
                if self.use_ga_response:
                    v_row = matching.iloc[0].copy()
                    v_row['Rank'] = rank
                    v_row['RowType'] = 'Variant'
                    paired_variant_rows.append(v_row)
                else:
                    for _, v_row in matching.iterrows():
                        v_row_copy = v_row.copy()
                        v_row_copy['Rank'] = rank
                        v_row_copy['RowType'] = 'Variant'
                        paired_variant_rows.append(v_row_copy)

        if paired_variant_rows:
            paired_variant_df = pd.DataFrame(paired_variant_rows)
            plot_data = pd.concat([deltas_plot_data, paired_variant_df], ignore_index=True)
            print(f"Plotting {len(deltas_plot_data)} deltas and {len(paired_variant_df)} variants")
        else:
            print("No variant data found in compiled data")
            plot_data = deltas_plot_data

        return plot_data, 'DB Included Deltas with Paired Variants'

    def compute_pairs(self, compiled_data, channel):
        """Compute the delta-variant pair table for a given channel/baseline setting.

        Returns ``(delta_avg_response, prepared)`` where ``delta_avg_response`` is
        the per-pair table (or ``None``) and ``prepared`` is the `PreparedResponses`
        produced by `ResponseSpec` (holds the prepared data with a scalar response
        column plus thumbnail paths). Used by the interactive curation GUI so it can
        recompute pairs without triggering any plotting or DB writes.
        """
        spec = ResponseSpec(channel, use_baseline_correction=self.use_baseline_correction)
        prepared = spec.apply(compiled_data, spike_rates_col=self.spike_rates_col)
        self.use_ga_response = spec.use_ga_response
        pairs = self._compute_pairs_table(prepared.data, prepared.response_col)
        return pairs, prepared

    def _compute_pairs_table(self, compiled_data, response_col_name):
        """Compute the full delta-variant pair table (all pairs, with threshold-based
        ``Included`` flag) from prepared compiled data. Returns the DataFrame or None."""
        # Compute included variants from data (no DB dependency)
        included_variant_ids, variant_responses = self._compute_included_variants(compiled_data, response_col_name)
        if not included_variant_ids:
            print("No included variants found!")
            return None
        print(f"Found {len(included_variant_ids)} included variants")

        # Only DELTA-type stims are candidates to be the "delta" in a pair,
        # preventing variant/variant pairs from forming.
        deltas_data = compiled_data[compiled_data['StimType'] == StimType.REGIME_ESTIM_DELTA.value].copy()
        if deltas_data.empty:
            print("No REGIME_ESTIM_DELTA stimuli found!")
            return None

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
            return None

        paired_delta_ids = {r['StimSpecId'] for r in pair_records}
        deltas_data = deltas_data[deltas_data['StimSpecId'].isin(paired_delta_ids)].copy()
        pair_map = pd.DataFrame(pair_records).drop_duplicates()

        print(f"Found {len(pair_map)} delta-variant pairs")

        # Average response per (delta, paired_variant)
        deltas_merged = deltas_data.merge(pair_map, on='StimSpecId', how='inner')
        delta_avg_response = deltas_merged.groupby(['StimSpecId', 'PairedVariantId'])[
            response_col_name].mean().reset_index()
        delta_avg_response.rename(columns={response_col_name: 'Delta Response'}, inplace=True)

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

        return delta_avg_response

    def _build_plot_data_from_calculations(self, compiled_data, response_col_name):
        """Build plot data by computing variant/delta pairs and applying threshold logic."""
        delta_avg_response = self._compute_pairs_table(compiled_data, response_col_name)
        if delta_avg_response is None or delta_avg_response.empty:
            return None, None, None

        # Decide which pairs go into the plot
        if self.plot_mode == PLOT_MODE_PASSING:
            plot_subset = delta_avg_response[delta_avg_response['Included']].copy()
            title = 'Included Deltas with Paired Variants'
        else:  # PLOT_MODE_ALL
            plot_subset = delta_avg_response.copy()
            title = 'All Delta-Variant Pairs'

        if plot_subset.empty:
            print("No pairs to plot!")
            return None, None, delta_avg_response

        plot_subset['Rank'] = plot_subset['Ratio'].rank(ascending=True, method='first')

        # Build delta rows for plot
        plot_delta_ids = plot_subset['StimSpecId'].unique()
        deltas_raw = compiled_data[compiled_data['StimSpecId'].isin(plot_delta_ids)].copy()
        deltas_plot_data = plot_subset[['StimSpecId', 'Rank']].merge(
            deltas_raw, on='StimSpecId', how='inner'
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

        return plot_data, title, delta_avg_response

    def _compute_included_variants(self, compiled_data, response_col_name):
        """Compute included variants from compiled_data using the variant threshold."""
        variants = compiled_data[compiled_data['StimType'].isin(
            [StimType.REGIME_ESTIM_VARIANTS.value, StimType.REGIME_ESTIM_DELTA.value]
        )].copy()

        if variants.empty:
            return [], pd.DataFrame(columns=['StimSpecId', 'Response'])

        variants_grouped = variants.groupby('StimSpecId')[response_col_name].mean().reset_index()
        max_response = variants_grouped[response_col_name].max()
        cutoff = self.variant_threshold * max_response
        print(f"Variant selection: max response={max_response:.2f}, threshold={cutoff:.2f} ({self.variant_threshold*100:.0f}%)")

        included = variants_grouped[variants_grouped[response_col_name] >= cutoff].copy()
        included_ids = included['StimSpecId'].tolist()
        included_responses = included[['StimSpecId', response_col_name]].rename(
            columns={response_col_name: 'Response'}
        )
        return included_ids, included_responses

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

    def _save_deltas_to_db(self, delta_data, skip_prompt=False):
        """Save delta information to IncludedDeltas table.

        When ``skip_prompt`` is True the existing-data confirmation prompt is
        bypassed (the caller is responsible for confirming the overwrite, e.g.
        the curation GUI shows its own dialog before calling).
        """
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

            if existing_count > 0 and not skip_prompt:
                print(f"\nWARNING: IncludedDeltas table already contains {existing_count} entries!")
                response = input("Do you want to DELETE all existing data and replace it? (yes/no): ").strip().lower()

                if response not in ['yes', 'y']:
                    print("Operation cancelled. No changes made to database.")
                    return False

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
            return True

        except Exception as e:
            print(f"Warning: Could not save to database: {e}")
            if skip_prompt:
                raise
            return False


if __name__ == "__main__":
    main()
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

        # Collapse to one row per stimulus: mean response plus the descriptive
        # columns we need for layout and labelling. compiled_data has one row
        # per presentation, so a stimulus can appear multiple times.
        stim_summary = (
            compiled_data
            .groupby('StimSpecId', as_index=False)
            .agg({
                response_col: 'mean',
                'GenId': 'first',
                'Lineage': 'first',
                'ParentId': 'first',
                'StimType': 'first',
                'ThumbnailPath': 'first',
            })
        )

        # The variants whose production history we want to trace, one row each.
        variants = self.filter_for_variants(stim_summary).copy()
        variants = variants[variants['ParentId'].notna()]
        if variants.empty:
            print("No variants found to plot")
            return

        # One plot row per parent that produced variants. Within a row the
        # columns run left-to-right by generation (chronological) and, within a
        # generation, by response (highest first, then decreasing).
        variants = variants.sort_values(
            ['ParentId', 'GenId', response_col],
            ascending=[True, True, False],
            kind='stable',
        )
        variants['ColIndex'] = variants.groupby('ParentId').cumcount() + 1
        variants['ParentGroup'] = variants['ParentId']
        variants['RowType'] = 'Variant'

        # The left-most column (ColIndex 0) of each row is the parent's own
        # image. Only parents that actually produced variants get a row.
        parent_ids = variants['ParentId'].unique()
        parents = stim_summary[stim_summary['StimSpecId'].isin(parent_ids)].copy()
        parents['ColIndex'] = 0
        parents['ParentGroup'] = parents['StimSpecId']
        parents['RowType'] = 'Parent'

        plot_data = pd.concat([parents, variants], ignore_index=True)
        print(f"Plotting {len(parents)} parents and {len(variants)} variants "
              f"across {plot_data['ParentGroup'].nunique()} rows")

        visualize_params = {
            'cell_size': (200, 200),
            'response_rate_col': response_col,
            'path_col': 'ThumbnailPath',
            'row_col': 'ParentGroup',
            'col_col': 'ColIndex',
            'cols_in_info_box': ["Response", "GenId", "StimSpecId"],
            # Interactive HTML instead of a PNG: the full-history grid is far
            # too large to rasterize, but a browser can scroll and zoom it.
            'save_path': f"{self.save_path}/{prepared.channel_label}{prepared.baseline_suffix}_variant_history_by_parent.html",
            'save_html': True,
            'open_in_browser': True,
            'module_name': "Variant_History_By_Parent",
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
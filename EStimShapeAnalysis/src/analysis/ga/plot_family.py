from __future__ import annotations

import pandas as pd
from matplotlib import pyplot as plt

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.pipeline.pipeline_base_classes import create_pipeline
from clat.util.connection import Connection
from src.analysis.fields.cached_task_fields import StimTypeField, StimPathField, ThumbnailField, ClusterResponseField
from src.analysis.fields.matchstick_fields import ShaftField, TerminationField, JunctionField, StimSpecDataField
from src.analysis.ga.cached_ga_fields import LineageField, GAResponseField, RegimeScoreField, GenIdField, ParentIdField
from src.analysis.isogabor.old_isogabor_analysis import IntanSpikesByChannelField, EpochStartStopTimesField, \
    IntanSpikeRateByChannelField
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.analysis.ga.plot_top_n import PlotTopNAnalysis, add_lineage_rank_to_df
from src.intan.MultiFileParser import MultiFileParser
from src.repository.export_to_repository import export_to_repository, read_session_id_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    analysis = PlotFamilyAnalysis()
    compiled_data = None
    # compiled_data = analysis.compile_and_export()
    session_id, _ = read_session_id_from_db_name(context.ga_database)
    session_id = "260115_0"
    # channels = "A-020"
    channels = read_cluster_channels(session_id)

    analysis.run(session_id, "raw", channels, compiled_data=compiled_data)


class PlotFamilyAnalysis(PlotTopNAnalysis):
    """
    Analysis to visualize the complete ancestry of top-performing stimuli.

    For each of the top N stimuli, traces back through ParentId to the founder
    and displays the full lineage in a row, with each stimulus colored by its
    response rate.
    """

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        # Add spike rate column for the specified channel(s)
        compiled_data = add_lineage_rank_to_df(compiled_data, self.spike_rates_col, channel)

        # Get top N stimuli based on response rate
        top_n = 10  # Number of top stimuli to show
        top_stimuli = get_top_n_stimuli(compiled_data, top_n)

        print(f"Found {len(top_stimuli)} top stimuli: {top_stimuli}")

        # Build family tree data
        family_data = build_family_tree_data(compiled_data, top_stimuli)

        print(f"Built family tree with {len(family_data)} total rows")
        print(f"Number of families: {family_data['FamilyId'].nunique() if not family_data.empty else 0}")

        # Generate appropriate filename based on channel type
        if isinstance(channel, list):
            channel_str = f"{len(channel)}_channels"
            response_key = channel
        else:
            channel_str = channel
            response_key = channel

        # Create visualization module
        visualize_module = create_grouped_stimuli_module(
            response_rate_col=self.spike_rates_col,
            response_rate_key=response_key,
            path_col='ThumbnailPath',
            row_col='FamilyId',
            col_col='PositionInFamily',
            title=f'Top {top_n} Stimuli Families',
            save_path=f"{self.save_path}/{channel_str}_plot_family.png",
            publish_mode=False,
            save_pdf=True,
            subplot_spacing=(20, 0),
            module_name="plot_family",
            border_width=50
        )

        # Create and run pipeline
        pipeline = create_pipeline().then(visualize_module).build()
        result = pipeline.run(family_data)

        plt.show()
        return result

    def compile_and_export(self):
        """Override to include ParentId in compilation"""
        data = self.compile()
        export_to_repository(data, context.ga_database, "ga",
                             stim_info_table="GAStimInfo",
                             stim_info_columns=[
                                 "Lineage",
                                 "RegimeScore",
                                 "GenId",
                                 "ParentId",  # Added ParentId
                                 "StimType",
                                 "StimPath",
                                 "ThumbnailPath",
                                 "GA Response",
                                 "Cluster Response",
                                 "Shaft",
                                 "Termination",
                                 "Junction"
                             ])
        return data

    def compile(self):
        """Override to include ParentId in compilation"""
        conn = Connection(context.ga_database)
        data_for_all_tasks = compile_data_with_parent(conn)

        # Import cleaning functions from plot_top_n
        from src.analysis.plot_top_n import clean_ga_data
        from src.pga.mock.mock_rwa_analysis import condition_spherical_angles, hemisphericalize_orientation

        data = clean_ga_data(data_for_all_tasks)
        data = condition_spherical_angles(data)
        data = hemisphericalize_orientation(data)
        return data


def compile_data_with_parent(conn: Connection) -> pd.DataFrame:
    """
    Compile data including ParentId field for ancestry tracing.
    """
    collector = TaskIdCollector(conn)
    task_ids = collector.collect_task_ids()
    response_processor = context.ga_config.make_response_processor()
    cluster_combination_strategy = response_processor.cluster_combination_strategy
    parser = MultiFileParser(to_cache=True, cache_dir=context.ga_parsed_spikes_path)
    mstick_spec_data_source = StimSpecDataField(conn)

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(LineageField(conn))
    fields.append(GenIdField(conn))
    fields.append(ParentIdField(conn))  # Added ParentId
    fields.append(RegimeScoreField(conn))
    fields.append(StimTypeField(conn))
    fields.append(StimPathField(conn))
    fields.append(ThumbnailField(conn))
    fields.append(GAResponseField(conn))
    fields.append(ClusterResponseField(conn, cluster_combination_strategy))
    fields.append(IntanSpikesByChannelField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(IntanSpikeRateByChannelField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(EpochStartStopTimesField(conn, parser, task_ids, context.ga_intan_path))
    fields.append(ShaftField(conn, mstick_spec_data_source))
    fields.append(TerminationField(conn, mstick_spec_data_source))
    fields.append(JunctionField(conn, mstick_spec_data_source))

    data = fields.to_data(task_ids)
    return data


def get_top_n_stimuli(compiled_data: pd.DataFrame, n: int) -> list:
    """
    Get the top N stimuli by average spike rate.

    Args:
        compiled_data: DataFrame with 'Spike Rate' column already added
        n: Number of top stimuli to return

    Returns:
        List of StimSpecIds for the top N stimuli
    """
    # Calculate average response rate for each StimSpecId
    avg_response = compiled_data.groupby('StimSpecId')['Spike Rate'].mean().reset_index()

    # Sort by response rate and get top N
    top_n = avg_response.nlargest(n, 'Spike Rate')

    return top_n['StimSpecId'].tolist()


def build_family_tree_data(compiled_data: pd.DataFrame, top_stimuli: list) -> pd.DataFrame:
    """
    Build a dataframe with family tree information for the top stimuli.

    For each top stimulus, traces back through ParentId to build the complete
    ancestry from founder to the top stimulus. Each top stimulus gets its own
    row (FamilyId), with stimuli ordered by their position in the lineage
    (PositionInFamily).

    Args:
        compiled_data: Full compiled data with ParentId column
        top_stimuli: List of StimSpecIds for the top stimuli

    Returns:
        DataFrame with FamilyId and PositionInFamily columns added
    """
    # Build a list of rows for the family tree
    family_rows = []

    for family_idx, top_stim_id in enumerate(top_stimuli):
        # Trace ancestry for this top stimulus
        ancestry = trace_ancestry(compiled_data, top_stim_id)

        print(f"Family {family_idx} (top stim {top_stim_id}): {len(ancestry)} ancestors: {ancestry}")

        # Add each ancestor to the family tree with position
        for position, stim_id in enumerate(ancestry):
            # Get all rows for this stimulus
            stim_rows = compiled_data[compiled_data['StimSpecId'] == stim_id].copy()

            if stim_rows.empty:
                print(f"  Warning: No data found for stimulus {stim_id} in family {family_idx}")
                continue

            # Add family information
            stim_rows['FamilyId'] = family_idx
            stim_rows['PositionInFamily'] = position

            family_rows.append(stim_rows)

    # Combine all family rows
    if family_rows:
        family_data = pd.concat(family_rows, ignore_index=True)
    else:
        family_data = pd.DataFrame()

    return family_data


def trace_ancestry(compiled_data: pd.DataFrame, stim_id: int) -> list:
    """
    Trace the ancestry of a stimulus back to its founder.

    Walks backward through ParentId links until reaching a founder (stimulus
    with no parent or ParentId = 0).

    Args:
        compiled_data: Full compiled data with ParentId column
        stim_id: StimSpecId to trace ancestry for

    Returns:
        List of StimSpecIds from founder to the given stimulus (in chronological order)
    """
    ancestry = [stim_id]
    current_id = stim_id

    # Build a mapping of StimSpecId to ParentId for efficient lookup
    stim_to_parent = compiled_data[['StimSpecId', 'ParentId']].drop_duplicates()
    stim_to_parent_dict = dict(zip(stim_to_parent['StimSpecId'], stim_to_parent['ParentId']))

    # Trace back through parents (with cycle detection)
    max_depth = 100  # Prevent infinite loops
    depth = 0

    while current_id in stim_to_parent_dict and depth < max_depth:
        parent_id = stim_to_parent_dict[current_id]

        # Check if parent exists (founder stimuli have no parent or parent = 0)
        if pd.isna(parent_id) or parent_id == 0:
            break

        # Check for cycles
        if parent_id in ancestry:
            print(f"Warning: Cycle detected in ancestry for stimulus {stim_id} at parent {parent_id}")
            break

        # Add parent to ancestry and continue
        ancestry.append(parent_id)
        current_id = parent_id
        depth += 1

    # Reverse to get chronological order (founder first)
    ancestry.reverse()

    return ancestry


if __name__ == "__main__":
    main()
import pandas as pd
from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import create_pipeline, create_branch
from src.analysis.ga import plot_top_n
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.response_spec import ResponseSpec
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    session_id = "250425_0"
    channel = "A-002"
    analysis = PlotGenerationsAnalysis()
    # compiled_data = None
    compiled_data = plot_top_n.compile_and_export()

    session_id, _ = read_session_id_and_date_from_db_name(context.ga_database)
    # session_id = "260115_0"
    channel = read_cluster_channels(session_id)
    # channel = ["A-009", "A-000", "A-006", "A-009", "A-015", "A-022", "A-024"]
    data_type = "GA" if channel == "GA" else "raw"
    analysis.run(session_id, data_type, channel, compiled_data=compiled_data)


class PlotGenerationsAnalysis(PlotTopNAnalysis):
    save_path = context.ga_plot_path

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

        # Find any lineages with more than 10 stimuli
        lineage_counts = compiled_data['Lineage'].value_counts()
        top_lineages = lineage_counts[lineage_counts > 10].index
        print(f"Top {top_lineages.size} lineages: {top_lineages} with counts")

        # Calculate average response rate for each StimSpecId within each subplot_Lineage
        avg_response = compiled_data.groupby(['GenId', 'StimSpecId', 'Lineage'])[response_col].mean().reset_index()
        avg_response.rename(columns={response_col: 'Avg Response Rate'}, inplace=True)
        avg_response['RankWithinGeneration'] = avg_response.groupby(['GenId', 'Lineage'])['Avg Response Rate'].rank(
            ascending=False, method='first')

        compiled_data = compiled_data.merge(avg_response[['GenId', 'StimSpecId', 'RankWithinGeneration']],
                                            on=['GenId', 'StimSpecId'],
                                            how='left')

        # For the first generation module - create ranking within first generation only
        first_gen_data = compiled_data[compiled_data['GenId'] == 1].copy()
        first_gen_avg = first_gen_data.groupby('StimSpecId')[response_col].mean().reset_index()
        first_gen_avg['FirstGenRank'] = first_gen_avg[response_col].rank(ascending=False, method='first')

        compiled_data = compiled_data.merge(
            first_gen_avg[['StimSpecId', 'FirstGenRank']],
            on='StimSpecId',
            how='left'
        )

        # 20x4 grid layout (80 total) — only for rows with FirstGenRank
        compiled_data['FirstGenRankRow'] = compiled_data['FirstGenRank'].apply(
            lambda x: int((x - 1) // 20) if pd.notna(x) else None
        )
        compiled_data['FirstGenRankCol'] = compiled_data['FirstGenRank'].apply(
            lambda x: int((x - 1) % 20) if pd.notna(x) else None
        )

        common_viz = dict(
            response_rate_col=response_col,
            path_col='ThumbnailPath',
        )
        if prepared.response_key is not None:
            common_viz['response_rate_key'] = prepared.response_key

        visualize_module = create_grouped_stimuli_module(
            **common_viz,
            cell_size=(100, 100),
            col_col='RankWithinGeneration',
            row_col='GenId',
            subgroup_col='Lineage',
            filter_values={
                "RankWithinGeneration": range(0, 15),
                "Lineage": top_lineages,
            },
            save_path=f"{self.save_path}/{prepared.channel_label}{prepared.baseline_suffix}_top_per_gen_by_lineage.png",
            module_name="Top Stimuli Per Gen by Lineage",
            publish_mode=True,
            save_pdf=True,
            border_width=75,
            subplot_spacing=(75, 25),
        )

        first_gen_module = create_grouped_stimuli_module(
            **common_viz,
            col_col='FirstGenRankCol',
            row_col='FirstGenRankRow',
            filter_values={
                "GenId": [1],
                "FirstGenRank": range(1, 81)
            },
            cell_size=(150, 150),
            save_path=f"{self.save_path}/{prepared.channel_label}{prepared.baseline_suffix}_first_gen_all80.png",
            module_name="First Generation All 80",
            border_width=75,
            publish_mode=True,
        )

        lineage_branch = create_branch().then(visualize_module)
        first_gen_branch = create_branch().then(first_gen_module)
        pipeline = create_pipeline().make_branch(lineage_branch, first_gen_branch).build()
        result = pipeline.run(compiled_data)
        plt.show()


if __name__ == "__main__":
    main()

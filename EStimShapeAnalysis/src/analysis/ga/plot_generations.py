import pandas as pd
from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import create_pipeline, create_branch
from src.analysis.ga import plot_top_n
from src.analysis.ga.plot_top_n import PlotTopNAnalysis, clean_ga_data
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.repository.export_to_repository import read_session_id_from_db_name
from src.repository.import_from_repository import import_from_repository
from src.startup import context


def main():
    session_id = "250425_0"
    channel = "A-002"
    analysis = PlotGenerationsAnalysis()
    compiled_data = plot_top_n.compile()

    session_id, _ = read_session_id_from_db_name(context.ga_database)
    session_id = "251219_0"
    channel = "A-016"
    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


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

        compiled_data = compiled_data[compiled_data[self.spike_rates_col].notna()]
        compiled_data['Spike Rate'] = compiled_data[self.spike_rates_col].apply(
            lambda x: x[channel] if channel in x else 0)

        # Find any lineages with more than 20 stimuli:
        lineage_counts = compiled_data['Lineage'].value_counts()
        top_lineages = lineage_counts[lineage_counts > 10].index

        print(f"Top {top_lineages.size} lineages: {top_lineages} with counts")




        # Calculate average response rate for each StimSpecId within each subplot_Lineage
        avg_response = compiled_data.groupby(['GenId', 'StimSpecId', 'Lineage'])['Spike Rate'].mean().reset_index()
        avg_response.rename(columns={'Spike Rate': 'Avg Response Rate'}, inplace=True)
        avg_response['RankWithinGeneration'] = avg_response.groupby(['GenId', 'Lineage'])['Avg Response Rate'].rank(ascending=False,
                                                                                                       method='first')

        # Merge the ranks back to the original dataframe
        compiled_data = compiled_data.merge(avg_response[['GenId', 'StimSpecId', 'RankWithinGeneration']],
                                            on=['GenId', 'StimSpecId'],
                                            how='left')

        # For the first generation module - create ranking within first generation only
        first_gen_data = compiled_data[compiled_data['GenId'] == 1].copy()
        first_gen_avg = first_gen_data.groupby('StimSpecId')['Spike Rate'].mean().reset_index()
        first_gen_avg['FirstGenRank'] = first_gen_avg['Spike Rate'].rank(ascending=False, method='first')

        # Merge back to main dataframe
        compiled_data = compiled_data.merge(
            first_gen_avg[['StimSpecId', 'FirstGenRank']],
            on='StimSpecId',
            how='left'
        )


        # Create row and column positions for 20x4 grid layout (80 total)
        # Create row and column positions for 20x4 grid layout (80 total) - only for rows with FirstGenRank
        compiled_data['FirstGenRankRow'] = compiled_data['FirstGenRank'].apply(
            lambda x: int((x - 1) // 20) if pd.notna(x) else None
        )
        compiled_data['FirstGenRankCol'] = compiled_data['FirstGenRank'].apply(
            lambda x: int((x - 1) % 20) if pd.notna(x) else None
        )

        visualize_module = create_grouped_stimuli_module(
            cell_size=(100,100),
            response_rate_col=self.spike_rates_col,
            response_rate_key=channel,
            path_col='ThumbnailPath',
            col_col='RankWithinGeneration',
            row_col='GenId',
            subgroup_col='Lineage',  # Add this line
            # title='Top Stimuli Per Gen',
            filter_values={
                "RankWithinGeneration": range(0, 10),
                "Lineage": top_lineages  # Add this line
                # "GenId": range(0,10)
            },  # only show top 20 per lineage
            # sort_rules={"GenId": "descending"},
            save_path=f"{self.save_path}/{channel}_top_per_gen_by_lineage.png",
            module_name="Top Stimuli Per Gen by Lineage",
            publish_mode=True
        )

        # Second module (first generation only, all 80 stimuli in 20x4 grid)
        first_gen_module = create_grouped_stimuli_module(
            response_rate_col=self.spike_rates_col,
            response_rate_key=channel,
            path_col='ThumbnailPath',
            col_col='FirstGenRankCol',  # 0-19 (20 columns)
            row_col='FirstGenRankRow',  # 0-3 (4 rows)
            filter_values={
                "GenId": [1],  # Only first generation
                "FirstGenRank": range(1, 81)  # All 80 stimuli (ranks 1-80)
            },
            cell_size=(150, 150),  # Smaller cells since we have 20 per row
            save_path=f"{self.save_path}/{channel}_first_gen_all80.png",
            module_name="First Generation All 80",
            publish_mode=True
        )

        # Create and run pipeline with aggregated data
        lineage_branch = create_branch().then(visualize_module)
        first_gen_branch = create_branch().then(first_gen_module)
        pipeline = create_pipeline().make_branch(lineage_branch, first_gen_branch).build()
        result = pipeline.run(compiled_data)
        plt.show()


if __name__ == "__main__":
    main()

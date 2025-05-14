from matplotlib import pyplot as plt

from clat.pipeline.pipeline_base_classes import create_pipeline
from src.analysis.ga import plot_top_n
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.modules.grouped_stims_by_response import create_grouped_stimuli_module
from src.repository.import_from_repository import import_from_repository


def main():
    session_id = "250507_0"
    channel = "A-002"
    analysis = PlotGenerationsAnalysis()
    compiled_data = plot_top_n.compile()

    # session_id, _ = read_session_id_from_db_name(context.ga_database)

    analysis.run(session_id, "raw", channel, compiled_data=compiled_data)


class PlotGenerationsAnalysis(PlotTopNAnalysis):
    def analyze(self, channel, compiled_data=None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        compiled_data['Spike Rate'] = compiled_data[self.spike_rates_col].apply(
            lambda x: x[channel] if channel in x else 0)
        # Calculate average response rate for each StimSpecId within each subplot_Lineage
        avg_response = compiled_data.groupby(['GenId', 'StimSpecId'])['Spike Rate'].mean().reset_index()
        avg_response.rename(columns={'Spike Rate': 'Avg Response Rate'}, inplace=True)
        avg_response['RankWithinGeneration'] = avg_response.groupby('GenId')['Avg Response Rate'].rank(ascending=False,
                                                                                                       method='first')

        # Merge the ranks back to the original dataframe
        compiled_data = compiled_data.merge(avg_response[['GenId', 'StimSpecId', 'RankWithinGeneration']],
                                            on=['GenId', 'StimSpecId'],
                                            how='left')

        visualize_module = create_grouped_stimuli_module(
            response_rate_col=self.spike_rates_col,
            response_rate_key=channel,
            path_col='ThumbnailPath',
            col_col='RankWithinGeneration',
            row_col='GenId',
            title='Top Stimuli Per Gen',
            filter_values={"RankWithinGeneration": range(0, 10),
                           # "GenId": range(0,10)
                           },  # only show top 20 per lineage
            # sort_rules={"GenId": "descending"},
            save_path=f"{self.save_path}/{channel}: top_per_gen.png",
        )

        # Create and run pipeline with aggregated data
        pipeline = create_pipeline().then(visualize_module).build()
        result = pipeline.run(compiled_data)
        plt.show()


if __name__ == "__main__":
    main()

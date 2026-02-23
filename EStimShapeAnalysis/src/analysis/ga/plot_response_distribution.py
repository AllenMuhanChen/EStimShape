import pandas as pd

from src.analysis import Analysis
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository


def main():
    analysis = PlotResponseDistributionAnalysis()
    session_id = "260115_0"
    channel = read_cluster_channels(session_id)
    analysis.run(session_id, "raw", channel, compiled_data=None)


class PlotResponseDistributionAnalysis(PlotTopNAnalysis):
    def analyze(self, channel, compiled_data: pd.DataFrame =None):
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        # Generate appropriate filename based on channel type
        if isinstance(channel, list):
            # Create a descriptive name for multiple channels
            channel_str = f"{len(channel)}_channels"
            # Use the response_rate_key as a list to sum dictionary values
            response_key = channel
        else:
            channel_str = channel
            response_key = channel

        print(compiled_data)

        #Make a new column 'Response' that sums the responses from the specified channels
        if isinstance(channel, list):
            def sum_channels(x):
                if not isinstance(x, dict):
                    return 0
                total = 0
                for ch in channel:
                    total += x.get(ch, 0)
                return total

            compiled_data['Response'] = compiled_data[self.spike_rates_col].apply(sum_channels)
        else:
            compiled_data['Response'] = compiled_data[self.spike_rates_col].apply(
                lambda x: x.get(channel, 0) if isinstance(x, dict) else 0
            )


        # Plot a histogram of responses using plotly
        import plotly.express as px
        fig = px.histogram(compiled_data, x='Response', nbins=50, title=f'Response Distribution for {channel_str}')
        fig.update_layout(xaxis_title='Response', yaxis_title='Count')
        fig.write_image(f"{self.save_path}/{channel_str}_response_distribution.png")
        fig.show()

        # Make a separate subplot per generation: GenId
        fig = px.histogram(compiled_data, x='Response', nbins=50, title=f'Response Distribution per Generation for {channel_str}', facet_row='GenId')
        fig.update_layout(xaxis_title='Response', yaxis_title='Count')

        # Add mean lines for each generation
        gen_ids = sorted(compiled_data['GenId'].unique())
        for i, gen_id in enumerate(gen_ids):
            gen_data = compiled_data[compiled_data['GenId'] == gen_id]
            mean_response = gen_data['Response'].mean()

            # Add vertical line for the mean
            fig.add_vline(
                x=mean_response,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Mean: {mean_response:.2f}",
                annotation_position="top",
                row=len(gen_ids) - i,
                col=1
            )


        fig.write_image(f"{self.save_path}/{channel_str}_response_distribution_per_generation.png")
        fig.show()




if __name__ == "__main__":
    main()
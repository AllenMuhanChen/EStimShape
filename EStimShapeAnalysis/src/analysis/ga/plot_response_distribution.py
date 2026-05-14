import pandas as pd

from src.analysis import Analysis
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.ga.response_spec import ResponseSpec
from src.repository.good_channels import read_cluster_channels
from src.repository.import_from_repository import import_from_repository


def main():
    analysis = PlotResponseDistributionAnalysis()
    session_id = "260115_0"
    channel = read_cluster_channels(session_id)
    data_type = "GA" if channel == "GA" else "raw"
    analysis.run(session_id, data_type, channel, compiled_data=None)


class PlotResponseDistributionAnalysis(PlotTopNAnalysis):
    def analyze(self, channel, compiled_data: pd.DataFrame = None):
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
        label = prepared.channel_label + prepared.baseline_suffix

        print(compiled_data)

        import plotly.express as px
        fig = px.histogram(compiled_data, x=response_col, nbins=50,
                           title=f'Response Distribution for {label}')
        fig.update_layout(xaxis_title='Response', yaxis_title='Count')
        fig.write_image(f"{self.save_path}/{label}_response_distribution.png")
        fig.show()

        fig = px.histogram(compiled_data, x=response_col, nbins=50,
                           title=f'Response Distribution per Generation for {label}',
                           facet_row='GenId')
        fig.update_layout(xaxis_title='Response', yaxis_title='Count')

        gen_ids = sorted(compiled_data['GenId'].unique())
        for i, gen_id in enumerate(gen_ids):
            gen_data = compiled_data[compiled_data['GenId'] == gen_id]
            mean_response = gen_data[response_col].mean()
            fig.add_vline(
                x=mean_response,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Mean: {mean_response:.2f}",
                annotation_position="top",
                row=len(gen_ids) - i,
                col=1
            )

        fig.write_image(f"{self.save_path}/{label}_response_distribution_per_generation.png")
        fig.show()




if __name__ == "__main__":
    main()
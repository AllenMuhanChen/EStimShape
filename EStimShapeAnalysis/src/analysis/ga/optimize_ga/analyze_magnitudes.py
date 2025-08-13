import pandas as pd

from clat.compile.task.cached_task_fields import CachedTaskFieldList
from clat.compile.task.classic_database_task_fields import StimSpecIdField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.util.connection import Connection
from src.analysis import Analysis
from src.analysis.fields.cached_task_fields import StimTypeField, StimPathField, ThumbnailField
from src.analysis.ga.cached_ga_fields import LineageField, GenIdField, RegimeScoreField, GAResponseField, \
    MutationMagnitudeField, ParentIdField
from src.startup import context
import plotly.express as px

def main():
    analysis = AnalyzeMagnitudesAnalysis()
    compiled_data = analysis.compile()
    analysis.analyze(None, compiled_data)

class AnalyzeMagnitudesAnalysis(Analysis):
    save_dir = '/home/connorlab/Documents/plots/ga_optimize'

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        # collapse down repetitions

        # filter out all mutation_magnitude = 0
        compiled_data = compiled_data[compiled_data['GA Response'].notna()]
        compiled_data = compiled_data[compiled_data['Mutation Magnitude'] != 0]


        # for each stim_id, get the difference between new response and old response
        # the response of the parent and the mutation magnitude
        grouped_data = compiled_data.groupby('StimSpecId').max()
        print(grouped_data.to_string())
        # plot scatterplot with x-axis being the magnitude and y-axis being the delta
        fig = px.scatter(grouped_data, x="Mutation Magnitude", y="Delta Response", color="Parent GA Response")
        fig.show()
        fig.write_image(f"{self.save_dir}/{self.session_id}_by_mutation_magnitude.png")

        fig2 = px.scatter(grouped_data, x="Parent GA Response", y="Delta Response", color="Mutation Magnitude")
        fig2.show()
        fig2.write_image(f"{self.save_dir}/{self.session_id}_by_parent_ga_response.png")


        # color the points based on the value of parent response
        pass

    def compile_and_export(self):
        pass

    def compile(self):
        conn = Connection(context.ga_database)
        collector = TaskIdCollector(conn)
        task_ids = collector.collect_task_ids()
        fields = CachedTaskFieldList()
        fields.append(StimSpecIdField(conn))
        fields.append(LineageField(conn))
        fields.append(GenIdField(conn))
        fields.append(RegimeScoreField(conn))
        fields.append(StimTypeField(conn))
        fields.append(StimPathField(conn))
        fields.append(ThumbnailField(conn))
        fields.append(GAResponseField(conn))
        fields.append(MutationMagnitudeField(conn))
        fields.append(ParentIdField(conn))
        fields.append(ParentGAResponseField(conn))
        fields.append(DeltaResponseField(conn))
        data = fields.to_data(task_ids)
        return data

class ParentGAResponseField(ParentIdField):
    def get(self, task_id) -> float:
        parent_id = self.get_cached_super(task_id, ParentIdField)
        self.conn.execute("SELECT response FROM StimGaInfo WHERE"
                          " stim_id=%s",
                          params=(parent_id,))
        parent_response = self.conn.fetch_one()
        return float(parent_response)

    def get_name(self):
        return "Parent GA Response"

class DeltaResponseField(ParentGAResponseField):
    def get(self, task_id) -> float:
        parent_response = self.get_cached_super(task_id, ParentGAResponseField)
        child_response = self.get_cached_super(task_id, GAResponseField)
        delta = child_response - parent_response
        return delta

    def get_name(self):
        return "Delta Response"

if __name__ == '__main__':
    main()

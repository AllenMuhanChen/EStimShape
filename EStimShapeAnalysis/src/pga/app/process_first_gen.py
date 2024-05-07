import numpy as np
import xmltodict

from clat.compile.task.base_database_fields import StimSpecIdField, StimSpecField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.compile.task.task_field import TaskFieldList, TaskField
from pga.multi_ga_db_util import MultiGaDbUtil
from startup import config


def main():
    ga = config.ga_config.make_genetic_algorithm()
    parser = ga.response_parser
    parser.parse_to_db(config.ga_name)

    calculate_spontaneous_firing()


def calculate_spontaneous_firing():
    conn = config.ga_config.connection
    task_id_collector = TaskIdCollector(conn)
    task_ids = task_id_collector.collect_task_ids()


    fields = TaskFieldList()
    fields.append(TaskField(name="TaskId"))
    fields.append(StimSpecIdField(conn))
    fields.append(StimPathField(conn))
    data = fields.to_data(task_ids)

    # filter to dataframe with path = "catch"
    data = data[data["path"] == "catch"]

    db_util = MultiGaDbUtil(conn)
    current_gen_id = db_util.read_ready_gas_and_generations_info().get(config.ga_name)

    cluster_channels = db_util.read_current_cluster(config.ga_name)

    # for each stimId:
    for channel in cluster_channels:
        for stim_id in data["StimSpecId"]:
            responses = db_util.read_responses_for(stim_id)
            mean_response = np.mean(responses)
            print("The mean response for stimId {} on channel {} is {}".format(stim_id, channel.value, mean_response))



class ChannelResponseField(StimSpecField):
    def __init__(self, conn, channel):
        super().__init__(conn, name=channel)
        self.db_util = MultiGaDbUtil(conn)
        self.cluster_channels = self.db_util.read_current_cluster(config.ga_name)

    def get(self, task_id):
        self.db_util.read_responses_for(task_id, )


class StimPathField(StimSpecField):
    def __init__(self, conn):
        super().__init__(conn, name="path")

    def get(self, task_id):
        stim_spec_field = super().get(task_id)
        stim_spec = xmltodict.parse(stim_spec_field)
        return stim_spec["StimSpec"]["path"]


if __name__ == "__main__":
    main()

import numpy as np
import xmltodict
from clat.compile.task.cached_task_fields import CachedTaskFieldList

from clat.compile.task.classic_database_task_fields import StimSpecIdField, StimSpecField
from clat.compile.task.compile_task_id import TaskIdCollector
from clat.compile.task.task_field import TaskFieldList, TaskField
from src.pga.multi_ga_db_util import MultiGaDbUtil
from src.startup import context


def main():
    calculate_spontaneous_firing()


def calculate_spontaneous_firing():
    conn = context.ga_config.connection()
    task_id_collector = TaskIdCollector(conn)
    task_ids = task_id_collector.collect_task_ids()

    fields = CachedTaskFieldList()
    fields.append(StimSpecIdField(conn))
    fields.append(StimPathField(conn))
    data = fields.to_data(task_ids)

    # filter to dataframe with path = "catch"
    data = data[data["path"] == "catch"]

    db_util = MultiGaDbUtil(conn)
    current_gen_id = db_util.read_ready_gas_and_generations_info().get(context.ga_name)
    current_experiment_id = db_util.read_current_experiment_id(context.ga_name)

    cluster_channels = db_util.read_current_cluster(context.ga_name)

    # calculate mean response for each cluster channel for catch trials
    mean_responses_for_channels = []
    for channel in cluster_channels:
        for stim_id in data["StimSpecId"]:
            responses = db_util.read_responses_for(stim_id, channel=channel.value)
            # Filter out NaN values from responses
            valid_responses = np.array(responses)[~np.isnan(responses)]
            if valid_responses.size > 0:
                mean_response_for_channel = np.mean(valid_responses)
                mean_responses_for_channels.append(mean_response_for_channel)
                print(
                    "The mean spontaneous firing rate for stimId {} on channel {} is {}".format(stim_id, channel.value,
                                                                                                mean_response_for_channel))
            else:
                print("No valid responses for stimId {} on channel {}. Defaulting to zero.".format(stim_id,
                                                                                                   channel.value))
                mean_responses_for_channels.append(0)  # Append 0 or some default value if no valid responses

    # calculate mean response of all cluster channels
    mean_response_for_all_cluster_channels = np.mean(mean_responses_for_channels)
    print("The mean spontaneous firing rate for all cluster channels is {}".format(
        mean_response_for_all_cluster_channels))

    # Update GAVar table with the calculated mean response for all cluster channels
    db_util.update_ga_var("regime_zero_transition_spontaneous_firing_rate",
                          current_gen_id,
                          current_experiment_id,
                          0,
                          mean_response_for_all_cluster_channels)


class ChannelResponseField(StimSpecField):
    def __init__(self, conn, channel):
        super().__init__(conn)
        self.name = channel
        self.db_util = MultiGaDbUtil(conn)
        self.cluster_channels = self.db_util.read_current_cluster(context.ga_name)

    def get(self, task_id):
        self.db_util.read_responses_for(task_id, )

    def get_name(self) -> str:
        return self.channel


class StimPathField(StimSpecField):
    def __init__(self, conn):
        super().__init__(conn)

    def get(self, task_id: int):
        stim_spec_field = self.get_cached_super(task_id, StimSpecField)
        stim_spec = xmltodict.parse(stim_spec_field)
        return stim_spec["StimSpec"]["path"]

    def get_name(self) -> str:
        return "path"


if __name__ == "__main__":
    main()

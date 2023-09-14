from compile.task.task_field import TaskField
from intan.channels import Channel


class SpikeTimesForChannelsField_Experiment(TaskField):
    def __init__(self, spike_times_for_channels_by_task_id):
        super().__init__("SpikeTimes")
        self.spike_times_for_channels_by_task_id = spike_times_for_channels_by_task_id

    def get(self, task_id: int):
        if task_id not in self.spike_times_for_channels_by_task_id:
            return None
        return self.spike_times_for_channels_by_task_id[task_id]

class EpochStartStopField_Experiment(TaskField):
    def __init__(self, epoch_start_stop_by_task_id):
        super().__init__("EpochStartStop")
        self.epoch_start_stop_by_task_id = epoch_start_stop_by_task_id

    def get(self, task_id: int):
        if task_id not in self.epoch_start_stop_by_task_id:
            return None
        return self.epoch_start_stop_by_task_id[task_id]
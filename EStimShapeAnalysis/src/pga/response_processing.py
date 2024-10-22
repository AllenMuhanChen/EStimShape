from dataclasses import dataclass
from typing import Callable

from src.pga.multi_ga_db_util import MultiGaDbUtil


@dataclass(kw_only=True)
class ResponseProcessor:
    db_util: MultiGaDbUtil
    repetition_combination_strategy: Callable[[list[float]], float]
    cluster_combination_strategy: Callable[[list[float]], int] #TODO: this currently isn't being
    # used, but it should be used to combine the responses from the different channels into a single

    def process_to_db(self, ga_name: str) -> None:
        # Aggregate responses to process
        response_vectors_for_each_stim_id = self._get_response_vectors_from_clusters(ga_name)

        # Process responses
        driving_response_for_each_stim_id = self._process_responses(response_vectors_for_each_stim_id)

        # Write processed responses to database
        for stim_id, driving_response in driving_response_for_each_stim_id.items():
            self.db_util.update_driving_response(stim_id, driving_response)

    def fetch_response_vector_for(self, stim_id, *, ga_name: str):
        cluster_channels = self.db_util.read_current_cluster(ga_name)
        vector_per_channel = {}
        for channel in cluster_channels:
            responses_per_task = self.db_util.read_responses_for(stim_id, channel=channel.value)
            vector_per_channel[channel] = responses_per_task

        response_vector = []
        length_of_vectors = len(list(vector_per_channel.values())[0])
        for i in range(length_of_vectors):
            #TODO: REPLACE THIS WITH ACTUAL COMBINATION STRATEGY
            sum_for_task = 0
            for channel, vector in vector_per_channel.items():
                sum_for_task += vector[i]
            response_vector.append(sum_for_task)

        response_vector = [float(f) for f in response_vector]
        return response_vector

    def _get_response_vectors_from_clusters(self, ga_name) -> dict[int, list[float]]:
        stims_to_process = self.db_util.read_stims_with_no_driving_response()

        response_vector_for_each_stim: dict[int, list[float]] = {}
        for stim_id in stims_to_process:
            responses_for_stim_id = self.fetch_response_vector_for(stim_id, ga_name=ga_name)

            response_vector_for_each_stim[stim_id] = responses_for_stim_id

        return response_vector_for_each_stim

    def _process_responses(self, responses_to_process: dict[int, list[float]]) -> dict[int, float]:
        driving_responses_for_stim_ids = {}
        for stim_id, responses in responses_to_process.items():
            driving_response = self.repetition_combination_strategy(responses)
            driving_responses_for_stim_ids[stim_id] = driving_response
        return driving_responses_for_stim_ids

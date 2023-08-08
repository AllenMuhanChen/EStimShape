from dataclasses import dataclass
from typing import Callable

from newga.multi_ga_db_util import MultiGaDbUtil


@dataclass
class ResponseProcessor:
    db_util: MultiGaDbUtil
    response_processor: Callable[[list[float]], float]

    def process_to_db(self, ga_name: str) -> None:
        # Aggregate responses to process
        response_vectors_for_each_stim_id = self._get_response_vectors_from_clusters(ga_name)

        # Process responses
        driving_response_for_each_stim_id = self._process_responses(response_vectors_for_each_stim_id)

        # Write processed responses to database
        for stim_id, driving_response in driving_response_for_each_stim_id.items():
            self.db_util.update_driving_response(stim_id, driving_response)

    def fetch_response_vector_for(self, stim_id, *, ga_name: str):
        channels = self.db_util.read_current_cluster(ga_name)
        responses_for_stim_id = []
        for channel in channels:
            responses_per_task = self.db_util.read_responses_for(stim_id, channel=channel)
            responses_for_stim_id.append(responses_per_task)
        return responses_for_stim_id

    def _get_response_vectors_from_clusters(self, ga_name) -> dict[int, list[float]]:
        stims_to_process = self.db_util.read_stims_with_no_driving_response()

        response_vector_for_each_stim: dict[int, list[float]] = {}
        for stim_id in stims_to_process:
            responses_for_stim_id = self.fetch_response_vector_for(stim_id, ga_name=ga_name)

            response_vector_for_each_stim[stim_id] = responses_for_stim_id

        return response_vector_for_each_stim

    def _process_responses(self, responses_to_process: dict[int, list[float]]) -> dict[int, float]:
        driving_responses_for_stim_ids = {}
        for stim_id, responses_to_process in responses_to_process.items():
            driving_response = self.response_processor(responses_to_process)
            driving_responses_for_stim_ids[stim_id] = driving_response
        return driving_responses_for_stim_ids

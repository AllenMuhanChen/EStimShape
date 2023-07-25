from dataclasses import dataclass
from typing import Callable

from newga.multi_ga_db_util import MultiGaDbUtil


@dataclass
class ResponseProcessor:
    db_util: MultiGaDbUtil
    response_processor: Callable[[list[float]], float]

    def process_to_db(self, ga_name: str) -> None:
        # Aggregate responses to process
        responses_to_process_for_stim_ids = self._aggregate_responses_to_process(ga_name)

        # Process responses
        driving_response_for_stim_ids = self._process_responses(responses_to_process_for_stim_ids)

        # Write processed responses to database
        for stim_id, driving_response in driving_response_for_stim_ids.items():
            self.db_util.update_driving_response(stim_id, driving_response)

    def _process_responses(self, responses_to_process: dict[int, list[float]]) -> dict[int, float]:
        driving_responses_for_stim_ids = {}
        for stim_id, responses_to_process in responses_to_process.items():
            driving_response = self.response_processor(responses_to_process)
            driving_responses_for_stim_ids[stim_id] = driving_response
        return driving_responses_for_stim_ids

    def _aggregate_responses_to_process(self, ga_name) -> dict[int, list[float]]:
        # Read unprocessed stim_ids from database
        stims_to_process = self.db_util.read_stims_with_no_driving_response()
        # Read channels to process from database
        channels_to_process = self.db_util.read_current_cluster(ga_name)
        # Fetch spike/s for each stim_id and channel
        responses_to_process_for_stims = {}
        for stim_id in stims_to_process:
            responses = []
            for channel in channels_to_process:
                response = self.db_util.get_spikes_per_second_from(stim_id, channel=channel)
                responses.append(response)
            responses_to_process_for_stims[stim_id] = responses
        return responses_to_process_for_stims

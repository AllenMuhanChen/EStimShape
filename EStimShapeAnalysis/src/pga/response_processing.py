from dataclasses import dataclass
from typing import Callable

from src.pga.multi_ga_db_util import MultiGaDbUtil


@dataclass(kw_only=True)
class GAResponseProcessor:
    db_util: MultiGaDbUtil
    repetition_combination_strategy: Callable[[list[float]], float]
    cluster_combination_strategy: Callable[[list[float]], int]  # TODO: this currently isn't being

    # used, but it should be used to combine the responses from the different channels into a single

    def process_to_db(self, ga_name: str) -> None:
        # For each stim, combine their cluster responses for each repetition
        responses_for_each_stim_id = self._process_clusters(ga_name)

        # Process repetitions for each stim into driving response
        driving_response_for_each_stim_id = self._process_repetitions(responses_for_each_stim_id)

        # Write processed responses to database
        for stim_id, driving_response in driving_response_for_each_stim_id.items():
            self.db_util.update_driving_response(stim_id, float(driving_response))

    def fetch_response_vector_for_repetitions_of(self, stim_id, *, ga_name: str) -> list[float]:
        """
        response vector is defined as the response for each repetition of stim_id
        one response number is obtaind by combining the responses from all the cluster channels
        according to the cluster_combination_strategy
        """
        cluster_channels = self.db_util.read_current_cluster(ga_name)

        # Get the vector(responses to all the repetitions of stim_id) for each cluster channel
        vector_per_channel = {}
        for channel in cluster_channels:
            responses_per_repetition = self.db_util.read_responses_for(stim_id, channel=channel.value)
            vector_per_channel[channel] = responses_per_repetition

        # Combine the vectors for each channel into a single response vector
        response_vector = []
        number_of_repetitions = len(list(vector_per_channel.values())[0])
        # For each repetition
        for i in range(number_of_repetitions):

            # Save the responses for the current repetition from each channel
            # so we can combine them
            responses_for_current_rep_across_channels = []

            # Do the combining across channels
            for channel, responses_for_repetition in vector_per_channel.items():
                responses_for_current_rep_across_channels.append(responses_for_repetition[i])
            combined_response = self.cluster_combination_strategy(responses_for_current_rep_across_channels)
            response_vector.append(combined_response)

        response_vector = [float(f) for f in response_vector]
        return response_vector

    def _process_clusters(self, ga_name) -> dict[int, list[float]]:
        stims_to_process = self.db_util.read_stims_with_no_driving_response()

        response_vector_for_each_stim: dict[int, list[float]] = {}
        for stim_id in stims_to_process:
            responses_for_stim_id = self.fetch_response_vector_for_repetitions_of(stim_id, ga_name=ga_name)

            response_vector_for_each_stim[stim_id] = responses_for_stim_id

        return response_vector_for_each_stim

    def _process_repetitions(self, responses_to_process: dict[int, list[float]]) -> dict[int, float]:
        driving_responses_for_stim_ids = {}
        for stim_id, responses in responses_to_process.items():
            driving_response = self.repetition_combination_strategy(responses)
            driving_responses_for_stim_ids[stim_id] = driving_response
        return driving_responses_for_stim_ids

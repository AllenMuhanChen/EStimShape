import unittest
from unittest.mock import MagicMock, Mock

from clat.intan.channels import Channel

from src.pga.response_processing import GAResponseProcessor


class TestResponseProcessor(unittest.TestCase):
    def setUp(self):
        # This list will store the arguments passed to update_driving_response
        self.update_driving_response_args = []

        # Mock db_util methods
        self.db_util_mock = Mock()
        responses = [1, 2, 3]
        channels = [Channel.A_000, Channel.A_001, Channel.A_002]
        channels_vals = [channel.value for channel in channels]
        self.db_util_mock.read_stims_with_no_driving_response.return_value = responses
        self.db_util_mock.read_current_cluster.return_value = channels
        self.db_util_mock.read_responses_for = lambda stim_id, channel: [responses[channels_vals.index(channel)], responses[channels_vals.index(channel)], responses[channels_vals.index(channel)]]

        # Store the arguments passed to update_driving_response in self.update_driving_response_args
        self.db_util_mock.update_driving_response.side_effect = lambda stim_id, driving_response: self.update_driving_response_args.append(
            (stim_id, driving_response))

        # Define the response_processor as sum
        self.response_processor = sum

    def test_sum_cluster_combo(self):

        # Create an instance of ResponseProcessor
        rp = GAResponseProcessor(db_util=self.db_util_mock, repetition_combination_strategy=sum, cluster_combination_strategy=sum)

        # Call the process_to_db method
        rp.process_to_db('test_ga')

        # Check if the arguments of update_driving_response are correct
        expected_args = [(1, 18.0), (2, 18.0), (3, 18.0)]
        print(self.update_driving_response_args)
        self.assertEqual(self.update_driving_response_args, expected_args)


    def test_average_cluster_combo(self):

        #TESTING AVERAGE ONE
        average = lambda x: sum(x) / len(x)
        # Create an instance of ResponseProcessor
        rp = GAResponseProcessor(db_util=self.db_util_mock, repetition_combination_strategy=sum,
                                 cluster_combination_strategy=average)

        # Call the process_to_db method
        rp.process_to_db('test_ga')

        # Check if the arguments of update_driving_response are correct
        expected_args = [(1, 6.0), (2, 6.0), (3, 6.0)]
        print(self.update_driving_response_args)
        self.assertEqual(self.update_driving_response_args, expected_args)

if __name__ == "__main__":
    unittest.main()

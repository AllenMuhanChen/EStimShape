import unittest
from unittest.mock import MagicMock
from src.intan.response_processing import ResponseProcessor


class TestResponseProcessor(unittest.TestCase):
    def setUp(self):
        # This list will store the arguments passed to update_driving_response
        self.update_driving_response_args = []

        # Mock db_util methods
        self.db_util_mock = MagicMock()
        self.db_util_mock.read_stims_with_no_driving_response.return_value = [1, 2, 3]
        self.db_util_mock.read_current_cluster.return_value = [1, 2, 3]
        self.db_util_mock.get_spikes_per_second = lambda stim_id, channel: channel

        # Store the arguments passed to update_driving_response in self.update_driving_response_args
        self.db_util_mock.update_driving_response.side_effect = lambda stim_id, driving_response: self.update_driving_response_args.append(
            (stim_id, driving_response))

        # Define the response_processor as sum
        self.response_processor = sum

    def test_process_to_db(self):
        # Create an instance of ResponseProcessor
        rp = ResponseProcessor(self.db_util_mock, self.response_processor)

        # Call the process_to_db method
        rp.process_to_db('test_ga')

        # Check if the arguments of update_driving_response are correct
        expected_args = [(1, 6.0), (2, 6.0), (3, 6.0)]
        self.assertEqual(self.update_driving_response_args, expected_args)


if __name__ == "__main__":
    unittest.main()

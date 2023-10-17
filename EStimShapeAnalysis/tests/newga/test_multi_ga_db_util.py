from unittest import TestCase

from newga.multi_ga_db_util import MultiGaDbUtil
from clat.util.connection import Connection


class TestMultiGaDbUtil(TestCase):

    def setUp(self) -> None:
        super().setUp()
        connection = Connection("allen_estimshape_dev_230519")
        self.db_util = MultiGaDbUtil(connection)

    def test_read_ready_gas_and_generations_info(self):
        print(self.db_util.read_ready_gas_and_generations_info())

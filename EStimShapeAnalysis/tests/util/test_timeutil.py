import unittest
import datetime
from clat.util import time_util

class TestTimeStampMethods(unittest.TestCase):
    def test_today(self):
        actualToday = datetime.date.fromtimestamp(time_util.today().start / 1000000)
        expectedToday = datetime.date.today()
        self.assertEqual(expectedToday, actualToday)
        print(time_util.today().start)
        print(time_util.today().stop)

    def test_print(self):
        w = time_util.When(1,2)
        printed = w.__str__()
        print(w)
        self.assertEqual(printed, "(1,2)")

    def test_repr(self):
        w = time_util.When(1,2)
        repr = w.__repr__()
        self.assertEqual(repr, "(1,2)")

if __name__ == '__main__':
    unittest()


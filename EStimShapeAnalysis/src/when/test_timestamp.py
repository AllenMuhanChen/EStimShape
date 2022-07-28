import unittest
import datetime
import timeutil

class TestTimeStampMethods(unittest.TestCase):
    def test_today(self):
        actualToday = datetime.date.fromtimestamp(timeutil.today().start/1000000)
        expectedToday = datetime.date.today()
        self.assertEqual(expectedToday, actualToday)


if __name__ == '__main__':
    unittest()


import time
import datetime


class When:
    def __init__(self, start, stop):
        self.start = start
        self.stop = stop


def today():
    today = __unix(datetime.date.today())
    tomorrow = __unix(datetime.date.today() + datetime.timedelta(days=1))
    when = When(today, tomorrow)
    return when


def __now():
    return round(time.time() * 1000000)


def __unix(datetime: datetime.datetime):
    return round(time.mktime(datetime.timetuple()) * 1000000)


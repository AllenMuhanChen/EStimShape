import time
import datetime


class When:
    def __init__(self, start, stop):
        self.start = start
        self.stop = stop

    def tuple(self):
        return (self.start, self.stop)

    def __str__(self):
        return "({},{})".format(self.start, self.stop)

    def __repr__(self):
        return self.__str__()


def today() -> When:
    today = to_unix(datetime.date.today())
    tomorrow = to_unix(datetime.date.today() + datetime.timedelta(days=1))
    when = When(today, tomorrow)
    return when


def days_ago(x):
    start = to_unix(datetime.date.today() - datetime.timedelta(days=x))
    stop = now()
    when = When(start, stop)


def all():
    when = When(0, to_unix(datetime.date.fromisoformat('3022-01-01')))
    return when


def now():
    return round(time.time() * 1000000)


def to_unix(dt: datetime.datetime):
    return round(time.mktime(dt.timetuple()) * 1000000)

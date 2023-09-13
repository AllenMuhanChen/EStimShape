import xmltodict

from util.connection import Connection


class TaskIdCollector:
    def __init__(self, conn: Connection):
        self.conn = conn

    def collect_task_ids(self):
        print("Collecting task IDs")
        self.conn.execute(
            "SELECT msg FROM BehMsg WHERE type = 'SlideOff'"
        )
        slide_off_msgs = self.conn.fetch_all()
        task_ids = []
        for msg in slide_off_msgs:
            slide_event_dict = xmltodict.parse(msg[0])
            task_id = int(slide_event_dict['SlideEvent']['taskId'])
            task_ids.append(task_id)
        return task_ids


class PngSlideIdCollector:
    """
    For Julie's experiment
    """
    def __init__(self, conn: Connection):
        self.conn = conn

    def collect_complete_task_ids(self, time_range: tuple):
        print("Collecting task IDs from Complete Trials (SlideOff Events)")

        # Unpack the start and end times from the tuple
        start_time, end_time = time_range

        # Modify the SQL query to include a WHERE clause for the tstamp range
        self.conn.execute(
            f"SELECT msg FROM BehMsg WHERE type = 'SlideOff' AND tstamp BETWEEN {start_time} AND {end_time}"
        )

        slide_off_msgs = self.conn.fetch_all()
        task_ids = []
        for msg in slide_off_msgs:
            slide_event_dict = xmltodict.parse(msg[0])
            try:
                task_id = int(slide_event_dict['PngSlideEvent']['taskId'])
                task_ids.append(task_id)
            except KeyError:
                print("Ignored a non-PNG slide event")
        return task_ids


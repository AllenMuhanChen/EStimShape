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

        # Fetch all messages in the time range
        self.conn.execute(
            f"SELECT tstamp, type, msg FROM BehMsg WHERE tstamp BETWEEN {start_time} AND {end_time} ORDER BY tstamp ASC"
        )

        all_msgs = self.conn.fetch_all()

        slide_off = None
        task_ids = []
        for tstamp, msg_type, msg in all_msgs:
            if msg_type == 'SlideOff':
                slide_off = xmltodict.parse(msg)
            elif msg_type == 'TrialComplete' and slide_off:
                try:
                    task_id = int(slide_off['PngSlideEvent']['taskId'])
                    task_ids.append(task_id)
                except KeyError:
                    print("Ignored a non-PNG slide event")
                slide_off = None
            elif msg_type == 'TrialStop':
                slide_off = None

        return task_ids



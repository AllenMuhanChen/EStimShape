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

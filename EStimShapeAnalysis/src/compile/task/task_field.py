from collections import OrderedDict
from typing import List

import pandas as pd





class TaskField:
    def __init__(self, name: str = None):
        if name is None:
            self.name = type(self).__name__
        else:
            self.name = name

    def get(self, task_id: int):
        return task_id


class TaskFieldList(List[TaskField]):
    """List of Field types"""

    def get_df(self):
        import pandas as pd
        df = pd.DataFrame(columns=self.get_names())
        return df

    def get_names(self):
        return [field.name for field in self]


class Task:
    def __init__(self, task_id: int, fields: TaskFieldList):
        self.task_id = task_id
        self.fields = fields

    def append_to_data(self, data):
        field_values = [field.get(self.task_id) for field in self.fields]
        names = self.fields.get_names()
        new_row = OrderedDict(zip(names, field_values))
        data.append(new_row)

def get_data_from_tasks(fields: TaskFieldList, task_ids: list[int]) -> pd.DataFrame:
    task_list = [Task(task_id, fields) for task_id in task_ids]
    data = []
    for i, task in enumerate(task_list):
        print("working on", i, "out of", len(task_list))
        task.append_to_data(data)
    return pd.DataFrame(data)
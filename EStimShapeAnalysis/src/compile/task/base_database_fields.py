from compile.task.task_field import TaskField
from util.connection import Connection


class DatabaseField(TaskField):
    def __init__(self, conn: Connection, name: str = None):
        super().__init__(name)
        self.conn = conn  # Assuming that the database connection is passed to the field


class StimSpecIdField(DatabaseField):
    def __init__(self, conn: Connection, name: str = "StimSpecId"):
        super().__init__(conn, name)

    def get(self, task_id: int) -> int:
        # Assuming a method or query to fetch the StimSpecId based on task_id
        # For demonstration, let's assume a method get_stim_spec_id is defined in the Connection class
        stim_spec_id = self.get_stim_spec_id(task_id)
        return stim_spec_id

    def get_stim_spec_id(self, task_id: int) -> int:
        # Execute the query to get the StimSpecId based on task_id
        # Note: Replace the query with the appropriate one for your schema
        query = "SELECT stim_id FROM TaskToDo WHERE task_id = %s"
        params = (task_id,)
        self.conn.execute(query, params)
        stim_spec_id = self.conn.fetch_one()
        return stim_spec_id


class StimSpecField(StimSpecIdField):
    def __init__(self, conn: Connection, name: str = "StimSpec"):
        super().__init__(conn, name)

    def get(self, task_id: int):
        # Execute the query to get the StimSpec based on task_id
        # Note: Replace the query with the appropriate one for your schema
        stim_id = super().get(task_id)
        query = "SELECT spec FROM StimSpec WHERE id = %s"
        params = (stim_id,)
        self.conn.execute(query, params)
        stim_spec = self.conn.fetch_one()
        return stim_spec


class StimSpecDataField(StimSpecIdField):
    def __init__(self, conn: Connection, name: str = "StimSpecData"):
        super().__init__(conn, name)

    def get(self, task_id: int):
        # Execute the query to get the StimSpecData based on task_id
        # Note: Replace the query with the appropriate one for your schema
        stim_id = super().get(task_id)
        query = "SELECT data FROM StimSpec WHERE id = %s"
        params = (stim_id,)
        self.conn.execute(query, params)
        stim_spec_data = self.conn.fetch_one()
        return stim_spec_data

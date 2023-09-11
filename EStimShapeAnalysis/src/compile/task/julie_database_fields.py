from abc import abstractmethod

import xmltodict

from compile.task.base_database_fields import StimSpecField
from util.connection import Connection
import re


class FileNameField(StimSpecField):
    def __init__(self, *, conn_xper: Connection, name: str = "FileName"):
        super().__init__(conn_xper, name)

    def get(self, task_id: int) -> str:
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        picture_path = stim_spec_dict['StimSpec']['filePath']
        file_name = self.extract_filename_from_filepath(picture_path)
        return file_name

    def extract_filename_from_filepath(self, filepath: str) -> str:
        match = re.search(r'([^/]+)$', filepath)
        if match:
            return match.group(1)
        return None


class MonkeyIdField(FileNameField):

    def __init__(self, *, conn_xper: Connection, conn_photo: Connection, name: str = "MonkeyId"):
        super().__init__(conn_xper=conn_xper, name=name)
        self.conn_photo = conn_photo

    def get(self, task_id: int):
        filename = super().get(task_id)
        # read monkey_id for file_name
        query = "SELECT monkey_id FROM photo_metadata.finalStimuliTable WHERE file_name = %s"
        params = (filename,)
        self.conn_photo.execute(query, params)
        monkey_id = self.conn_photo.fetch_one()

        return monkey_id


class MonkeyNameField(MonkeyIdField):

    def __init__(self, *, conn_xper: Connection, conn_photo: Connection, name: str = "MonkeyName"):
        super().__init__(conn_xper=conn_xper, conn_photo=conn_photo, name=name)

    def get(self, task_id: int) -> str:
        monkey_id = super().get(task_id)
        # read monkey_name for monkey_id
        query = "SELECT monkey_name FROM photo_metadata.finalStimuliTable WHERE monkey_id = %s"
        params = (monkey_id,)
        self.conn_photo.execute(query, params)
        monkey_name = self.conn_photo.fetch_one()

        return monkey_name


class JpgIdField(FileNameField):

    def __init__(self, *, conn_xper: Connection, conn_photo: Connection, name: str = "JpgId"):
        super().__init__(conn_xper=conn_xper, name=name)
        self.conn_photo = conn_photo

    def get(self, task_id: int) -> int:
        filename = super().get(task_id)
        # read jpg_id for file_name
        query = "SELECT jpg_id FROM photo_metadata.finalStimuliTable WHERE file_name = %s"
        params = (filename,)
        self.conn_photo.execute(query, params)
        jpg_id = int(self.conn_photo.fetch_one())

        return jpg_id


class MonkeyGroupField(JpgIdField):

        def __init__(self, *, conn_xper: Connection, conn_photo: Connection, name: str = "MonkeyGroup"):
            super().__init__(conn_xper=conn_xper, conn_photo=conn_photo, name=name)

        def get(self, task_id: int) -> str:
            jpg_id = super().get(task_id)
            # read monkey_group for jpg_id
            query = "SELECT monkey_group FROM photo_metadata.photos WHERE jpg_id = %s"
            params = (jpg_id,)
            self.conn_photo.execute(query, params)
            monkey_group = self.conn_photo.fetch_one()

            return monkey_group


import xmltodict

from clat.compile.task.base_database_fields import StimSpecField
from clat.util.connection import Connection
import re


class FileNameField(StimSpecField):
    def __init__(self, *, conn_xper: Connection, name: str = "FileName"):
        super().__init__(conn_xper, name)

    def get(self, task_id: int) -> str:
        stim_spec = super().get(task_id)
        stim_spec_dict = xmltodict.parse(stim_spec)
        picture_path = stim_spec_dict['StimSpec']['filePath']
        file_name = self.extract_filename_from_filepath(picture_path)
        if self.is_new_monkey_picture(picture_path):
            #add new_monkey_ to the filename
            file_name = "new_monkey_" + file_name

        return file_name

    def is_new_monkey_picture(self, path: str):
        is_in_new_monkey_path = "new_monkey" in path
        is_macaque_in_filename = "macaque" in path
        return is_in_new_monkey_path or is_macaque_in_filename

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
        if "new_monkey" in filename:
            return -1
        try:
            monkey_id = re.search(r'(\d+)\.', filename).group(1)
        except AttributeError:
            monkey_id = None
            print("WARNING! No monkey_id found for file_name: " + str(filename))
        return monkey_id


class MonkeyNameField(MonkeyIdField):

    def __init__(self, *, conn_xper: Connection, conn_photo: Connection, name: str = "MonkeyName"):
        super().__init__(conn_xper=conn_xper, conn_photo=conn_photo, name=name)

    def get(self, task_id: int) -> str:
        monkey_id = super().get(task_id)
        if monkey_id == -1:
            return "NewMonkey"
        # read monkey_name for monkey_id
        query = "SELECT monkey_name FROM photo_metadata.combined_view WHERE monkey_id = %s"
        params = (monkey_id,)
        self.conn_photo.execute(query, params)
        monkey_name = self.conn_photo.fetch_one()

        return monkey_name


class JpgIdField(MonkeyIdField):

    def __init__(self, *, conn_xper: Connection, conn_photo: Connection, name: str = "JpgId"):
        super().__init__(conn_xper=conn_xper, conn_photo=conn_photo, name=name)


    def get(self, task_id: int) -> int:
        monkey_id = super().get(task_id)
        if monkey_id == -1:
            return -1
        # read jpg_id for file_name
        query = "SELECT jpg_id FROM photo_metadata.combined_view WHERE monkey_id = %s"
        params = (monkey_id,)
        self.conn_photo.execute(query, params)
        result = self.conn_photo.fetch_one()
        if result:
            jpg_id = int(result)
        else:
            jpg_id = None
            print("WARNING! No jpg_id found for monkey_id: " + str(monkey_id))

        return jpg_id


class MonkeyGroupField(JpgIdField):

        def __init__(self, *, conn_xper: Connection, conn_photo: Connection, name: str = "MonkeyGroup"):
            super().__init__(conn_xper=conn_xper, conn_photo=conn_photo, name=name)

        def get(self, task_id: int) -> str:
            jpg_id = super().get(task_id)
            if jpg_id == -1:
                return "Zombies"
            # read monkey_group for jpg_id
            query = "SELECT monkey_group FROM photo_metadata.photos WHERE jpg_id = %s"
            params = (jpg_id,)
            self.conn_photo.execute(query, params)
            monkey_group = self.conn_photo.fetch_one()

            return monkey_group


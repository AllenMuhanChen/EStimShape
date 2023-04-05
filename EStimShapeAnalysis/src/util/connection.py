import mysql.connector
import pandas as pd
from pandas import DataFrame

from src.util import time_util
from src.util.time_util import When


class Connection:

    def __init__(self, database, password="up2nite"):
        self.mydb = mysql.connector.connect(
            host="172.30.6.80",
            user="xper_rw",
            password=password,
            database=database
        )

        self.my_cursor = self.mydb.cursor()

    def execute(self, statement, params=()):
        self.my_cursor.execute(statement, params)

    def truncate(self, table_name):
        self.execute(f"TRUNCATE TABLE {table_name}")
        self.fetch_all()
        self.mydb.commit()

    def fetch_one(self):
        return "".join(map(str, self.my_cursor.fetchall()[0]))

    def get_beh_msg(self, when: When) -> pd.DataFrame:
        self.my_cursor.execute("SELECT * FROM BehMsg WHERE tstamp>= %s && tstamp<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.my_cursor.fetchall())
        df.columns = ['tstamp', 'type', 'msg']
        return df

    def get_stim_spec(self, when: When) -> pd.DataFrame:
        self.my_cursor.execute("SELECT * FROM StimSpec WHERE id>= %s & id<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.my_cursor.fetchall())
        df.columns = ['id', 'spec', 'util']
        return df

    def get_stim_obj_data(self, when: When) -> pd.DataFrame:
        try:
            self.my_cursor.execute("SELECT * FROM StimObjData WHERE id>= %s & id<=%s", (when.start, when.stop))
            df = pd.DataFrame(self.my_cursor.fetchall())
            df.columns = ['id', 'spec', 'util']
            return df
        except:
            return None

    def get_beh_msg_eye(self, when: When) -> pd.DataFrame:
        self.my_cursor.execute("SELECT * FROM BehMsgEye WHERE tstamp>= %s & tstamp<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.my_cursor.fetchall())
        df.columns = ['tstamp', 'type', 'msg']
        return df

    def fetch_all(self):
        return self.my_cursor.fetchall()

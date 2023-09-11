import threading
from time import sleep

import mysql.connector
import pandas as pd
from pandas import DataFrame

from src.util import time_util
from src.util.time_util import When


class Connection:

    def __init__(self, database, password="up2nite", host="172.30.6.80"):
        self.database = database
        self.password = password
        self.connect(database, password, host)
        self.lock = threading.Lock()

    def connect(self, database, password, host):
        self.my_cursor = None
        self.mydb = mysql.connector.connect(
            host=host,
            user="xper_rw",
            password=password,
            database=database,
            autocommit=True
        )

    def execute(self, statement, params=()):
        with self.lock:
            try:
                try:
                    self.my_cursor.fetchall()
                    self.my_cursor.close()
                except:
                    pass
                self.my_cursor = self.mydb.cursor()
            except mysql.connector.errors.OperationalError as e:
                sleep(1)
                self.connect(self.database, self.password)
                self.my_cursor = self.mydb.cursor()
            self.my_cursor.execute(statement, params)

            has_results = self.my_cursor.description is not None
            if not has_results:
                self.mydb.commit()
                self.my_cursor.close()

    def truncate(self, table_name):
        self.execute(f"TRUNCATE TABLE {table_name}")

    def fetch_one(self):
        with self.lock:
            result = None
            try:
                result = self.my_cursor.fetchone()
            except mysql.connector.errors.InternalError as e:
                if "Unread result found" in str(e):
                    self.my_cursor.fetchall()
                    result = self.my_cursor.fetchone()
            if result:
                return result[0]
            else:
                return None

    def fetch_all(self):
        with self.lock:
            result = self.my_cursor.fetchall()
            # self.my_cursor.fetchall()
            self.my_cursor.close()
            return result

    def get_beh_msg(self, when: When) -> pd.DataFrame:
        self.execute("SELECT * FROM BehMsg WHERE tstamp>= %s && tstamp<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.fetch_all())
        df.columns = ['tstamp', 'type', 'msg']
        return df

    def get_stim_spec(self, when: When) -> pd.DataFrame:
        self.execute("SELECT * FROM StimSpec WHERE id>= %s & id<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.fetch_all())
        df.columns = ['id', 'spec', 'util']
        return df

    def get_stim_obj_data(self, when: When) -> pd.DataFrame:
        try:
            self.execute("SELECT * FROM StimObjData WHERE id>= %s & id<=%s", (when.start, when.stop))
            df = pd.DataFrame(self.fetch_all())
            df.columns = ['id', 'spec', 'util']
            return df
        except:
            return None

    def get_beh_msg_eye(self, when: When) -> pd.DataFrame:
        self.execute("SELECT * FROM BehMsgEye WHERE tstamp>= %s & tstamp<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.fetch_all())
        df.columns = ['tstamp', 'type', 'msg']
        return df



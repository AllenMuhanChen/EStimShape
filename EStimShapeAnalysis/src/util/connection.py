import mysql.connector
import pandas as pd
from pandas import DataFrame

from src.util import time_util
from src.util.time_util import When


class Connection:
    beh_msg: DataFrame
    stim_spec: DataFrame
    stim_obj_data: DataFrame
    def __init__(self, database, password="up2nite", when=None):
        self.mydb = mysql.connector.connect(
            host="172.30.6.80",
            user="xper_rw",
            password=password,
            database=database
        )
        self.mycursor = self.mydb.cursor()
        if when is None:
            when = time_util.today()
        self.beh_msg = self._get_beh_msg(when)
        self.stim_spec = self._get_stim_sec(when)
        self.stim_obj_data = self._get_stim_obj_data(when)

    def _get_beh_msg(self, when: When) -> pd.DataFrame:
        self.mycursor.execute("SELECT * FROM BehMsg WHERE tstamp>= %s && tstamp<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.mycursor.fetchall())
        df.columns = ['tstamp', 'type', 'msg']
        return df

    def _get_stim_sec(self, when: When) -> pd.DataFrame:
        self.mycursor.execute("SELECT * FROM StimSpec WHERE id>= %s & id<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.mycursor.fetchall())
        df.columns = ['id', 'spec', 'util']
        return df

    def _get_stim_obj_data(self, when: When) -> pd.DataFrame:
        self.mycursor.execute("SELECT * FROM StimObjData WHERE id>= %s & id<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.mycursor.fetchall())
        df.columns = ['id', 'spec', 'util']
        return df
    def _get_beh_msg_eye(self, when: When) -> pd.DataFrame:
        self.mycursor.execute("SELECT * FROM BehMsgEye WHERE id>= %s & id<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.mycursor.fetchall())
        df.columns = ['tstamp', 'type', 'msg']
        return df

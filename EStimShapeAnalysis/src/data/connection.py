import mysql.connector
import pandas as pd
from src.data import timeutil


class Connection:
    def __init__(self, database, password="up2nite", when=None):
        self.mydb = mysql.connector.connect(
            host="172.30.6.80",
            user="xper_rw",
            password=password,
            database=database
        )
        self.mycursor = self.mydb.cursor()
        if when is None:
            when = timeutil.today()
        self.beh_msg = self._get_beh_msg(when)
        self.stim_spec = self._get_stim_sec(when)
        self.stim_obj_data = self._get_stim_obj_data(when)

    def _get_beh_msg(self, when) -> pd.DataFrame:
        self.mycursor.execute("SELECT * FROM BehMsg WHERE tstamp>= %s && tstamp<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.mycursor.fetchall())
        df.columns = ['tstamp', 'type', 'msg']
        return df

    def _get_stim_sec(self, when) -> pd.DataFrame:
        self.mycursor.execute("SELECT * FROM StimSpec WHERE id>= %s & id<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.mycursor.fetchall())
        df.columns = ['id', 'spec', 'data']
        return df

    def _get_stim_obj_data(self, when) -> pd.DataFrame:
        self.mycursor.execute("SELECT * FROM StimObjData WHERE id>= %s & id<=%s", (when.start, when.stop))
        df = pd.DataFrame(self.mycursor.fetchall())
        df.columns = ['id', 'spec', 'data']
        return df

import mysql.connector
import pandas as pd
from src.when import timeutil

mydb = mysql.connector.connect(
    host="172.30.6.80",
    user="xper_rw",
    password="up2nite",
    database="allen_estimshape_train_220725"
)
mycursor = mydb.cursor()
when = timeutil.today()

def get_beh_msg() -> pd.DataFrame:
    mycursor.execute("SELECT * FROM BehMsg WHERE tstamp>= %s & tstamp<=%s", (when.start, when.stop))
    df = pd.DataFrame(mycursor.fetchall())
    df.columns = ['tstamp', 'type', 'msg']
    return df


def get_stim_sec() -> pd.DataFrame:
    mycursor.execute("SELECT * FROM StimSpec WHERE id>= %s & id<=%s", (when.start, when.stop))
    df = pd.DataFrame(mycursor.fetchall())
    df.columns = ['id', 'spec', 'data']
    return df


def get_stim_obj_data() -> pd.DataFrame:
    mycursor.execute("SELECT * FROM StimObjData WHERE id>= %s & id<=%s", (when.start, when.stop))
    df = pd.DataFrame(mycursor.fetchall())
    df.columns = ['id', 'spec', 'data']
    return df

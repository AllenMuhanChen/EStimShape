from clat.util.connection import Connection
from src.startup import context
from src.pga.app import transfer_eye_cal_params

def insert_rfinfo_data(conn: Connection):
    """Insert the RFInfo data into the table."""

    # The data to insert
    tstamp = 1748445844542521
    info = """<RFInfo>
  <center>
    <x>-0.5619020643787096</x>
    <y>1.8266904855425596</y>
  </center>
  <radius>2.5443869029397392</radius>
  <outline class="linked-list">
    <org.xper.drawing.Coordinates2D>
      <x>9.37828371278465</x>
      <y>33.78159126365051</y>
    </org.xper.drawing.Coordinates2D>
    <org.xper.drawing.Coordinates2D>
      <x>-19.38178633975474</x>
      <y>-1.2511700468018603</y>
    </org.xper.drawing.Coordinates2D>
  </outline>
</RFInfo>"""
    channel = "SUPRA-000"

    insert_sql = """
    INSERT INTO RFInfo (tstamp, info, channel) 
    VALUES (%s, %s, %s)
    """

    conn.execute(insert_sql, params=(tstamp, info, channel))


def insert_rfobjectdata(conn: Connection):
    """Insert the RFObjectData entries into the table."""

    rfobject_data = [
        (None, 1748445844558730, "SUPRA-000", "org.xper.rfplot.drawing.RFPlotBlankObject"),
        ("1.0,0.0,0.0", 1748445844582381, "SUPRA-000", "org.xper.allen.rfplot.RFPlotMatchStick"),
        ("""<StimSpec animation="true">
  <xCenter>0.0</xCenter>
  <yCenter>0.0</yCenter>
  <orientation>25.0</orientation>
  <frequency>1.0</frequency>
  <phase>0.0</phase>
  <size>4.5</size>
  <color>
    <red>1.0</red>
    <green>0.0</green>
    <blue>0.0</blue>
  </color>
</StimSpec>""", 1748445844591082, "SUPRA-000", "org.xper.rfplot.drawing.gabor.Gabor"),
        ("length: 5.00, width: 1.00, orientation: 0.0", 1748445844612158, "SUPRA-000",
         "org.xper.rfplot.drawing.bar.RFPlotBar")
    ]

    insert_sql = """
    INSERT INTO RFObjectData (data, tstamp, channel, object) 
    VALUES (%s, %s, %s, %s)
    """

    for data, tstamp, channel, obj in rfobject_data:
        conn.execute(insert_sql, params=(data, tstamp, channel, obj))


def main():
    conn = Connection(context.ga_database)
    insert_rfinfo_data(conn)
    insert_rfobjectdata(conn)
    transfer_eye_cal_params.main()


if __name__ == "__main__":
    main()
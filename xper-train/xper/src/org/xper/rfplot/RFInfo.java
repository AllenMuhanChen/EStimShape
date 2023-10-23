package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.List;

public class RFInfo {
    List<Coordinates2D> outline;
    Coordinates2D center;


    public RFInfo(List<Coordinates2D> outline, Coordinates2D center) {
        this.outline = outline;
        this.center = center;
    }

    transient static XStream s;

    static {
        s = new XStream();
        s.alias("RFInfo", RFInfo.class);
    }

    public String toXml () {
        return s.toXML(this);
    }

    public static RFInfo fromXml (String xml) {
        RFInfo p = (RFInfo)s.fromXML(xml);
        return p;
    }

}
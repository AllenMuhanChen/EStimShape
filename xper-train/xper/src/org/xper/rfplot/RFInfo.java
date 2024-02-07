package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.List;

public class RFInfo {
    List<Coordinates2D> outline;
    Coordinates2D center;

    public RFInfo() {
    }

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

    public List<Coordinates2D> getOutline() {
        return outline;
    }

    public void setOutline(List<Coordinates2D> outline) {
        this.outline = outline;
    }

    public Coordinates2D getCenter() {
        return center;
    }

    public void setCenter(Coordinates2D center) {
        this.center = center;
    }
}
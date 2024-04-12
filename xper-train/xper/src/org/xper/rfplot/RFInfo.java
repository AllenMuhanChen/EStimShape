package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;

import java.util.List;

public class RFInfo {
    public List<Coordinates2D> outline;
    public Coordinates2D center;
    public double radius;

    public RFInfo() {
    }

    public RFInfo(List<Coordinates2D> outline, Coordinates2D center, double radius) {
        this.outline = outline;
        this.center = center;
        this.setRadius(radius);
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

    public double getRadius() {
        return radius;
    }

    public void setRadius(double radius) {
        this.radius = radius;
    }
}
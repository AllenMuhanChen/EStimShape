package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;

import java.util.List;

public class RFInfo {
    public Coordinates2D center;
    public double radius;

    public RFInfo() {
    }

    public RFInfo(Coordinates2D center, double radius) {
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
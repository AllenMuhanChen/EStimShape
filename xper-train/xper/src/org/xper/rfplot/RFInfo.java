package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;

import java.util.LinkedList;
import java.util.List;

public class RFInfo {
    public Coordinates2D center;
    public double radius;
    List<Coordinates2D> outline = new LinkedList<>();

    public RFInfo() {
    }

    /**
     *
     * @param center - in degrees
     * @param radius - in degrees
     * @param controlPoints - in mm, should be original control points without any conversion.
     *                      This is solely to reload the circles when reloading.
     */
    public RFInfo(Coordinates2D center, double radius, List<Coordinates2D> controlPoints) {
        this.center = center;
        this.setRadius(radius);
        this.outline = controlPoints;
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

    public List<Coordinates2D> getControlPoints() {
        return outline;
    }

    public void setControlPoints(List<Coordinates2D> controlPoints) {
        this.outline = controlPoints;
    }
}
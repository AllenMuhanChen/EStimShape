package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import java.util.List;

public class V4RFInfo extends RFInfo{

    public RGBColor color;

    public V4RFInfo(List<Coordinates2D> outline, Coordinates2D center, double radius, RGBColor color) {
        super(center, radius);
        this.setColor(color);
    }

    public V4RFInfo() {
    }

    static {
        s = new XStream();
        s.alias("RFInfo", V4RFInfo.class);
    }

    public String toXml () {
        return s.toXML(this);
    }

    public static V4RFInfo fromXml (String xml) {
        V4RFInfo p = (V4RFInfo)s.fromXML(xml);
        return p;
    }

    public RGBColor getColor() {
        return color;
    }

    public void setColor(RGBColor color) {
        this.color = color;
    }
}
package org.xper.fixtrain.drawing;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.RGBColor;

public class FixationPointSpec {
    double size;

    RGBColor color;

    boolean solid = true;

    public FixationPointSpec() {
    }

    static XStream s;
    static {
        s = new XStream();
        s.alias("FixationPointSpec", FixationPointSpec.class);
    }

    public String toXml () {
        return FixationPointSpec.toXml(this);
    }

    public static String toXml (FixationPointSpec spec) {
        return s.toXML(spec);
    }

    public static FixationPointSpec fromXml (String xml) {
        FixationPointSpec spec = (FixationPointSpec)s.fromXML(xml);
        return spec;
    }

    public double getSize() {
        return size;
    }

    public void setSize(double size) {
        this.size = size;
    }

    public RGBColor getColor() {
        return color;
    }

    public void setColor(RGBColor color) {
        this.color = color;
    }

    public boolean isSolid() {
        return solid;
    }

    public void setSolid(boolean solid) {
        this.solid = solid;
    }
}
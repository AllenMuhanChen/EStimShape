package org.xper.rfplot.drawing;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.RGBColor;

public class IsochromaticGaborSpec extends GaborSpec{
    RGBColor color;

    public RGBColor getColor() {
        return color;
    }

    public void setColor(RGBColor color) {
        this.color = color;
    }

    static {
        s = new XStream();
        s.alias("StimSpec", IsochromaticGaborSpec.class);
        s.useAttributeFor("animation", boolean.class);
    }

    public String toXml () {
        return IsochromaticGaborSpec.toXml(this);
    }

    public static String toXml (IsochromaticGaborSpec spec) {
        return s.toXML(spec);
    }

    public static IsochromaticGaborSpec fromXml (String xml) {
        IsochromaticGaborSpec g = (IsochromaticGaborSpec) s.fromXML(xml);
        return g;
    }
}
package org.xper.rfplot.drawing.gabor;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.GaborSpec;

public class IsoluminantGaborSpec extends GaborSpec {
    public String colors;

    public IsoluminantGaborSpec(GaborSpec d, String colors) {
        super(d);
        this.colors = colors;
    }



    public IsoluminantGaborSpec() {
    }

    static {
        s = new XStream();
        s.alias("StimSpec", IsoluminantGaborSpec.class);
        s.useAttributeFor("animation", boolean.class);
    }

    public String toXml() {
        return s.toXML(this);
    }

    public static IsoluminantGaborSpec fromXml(String xml) {
        return (IsoluminantGaborSpec)s.fromXML(xml);
    }


}
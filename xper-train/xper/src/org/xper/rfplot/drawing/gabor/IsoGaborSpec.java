package org.xper.rfplot.drawing.gabor;

import com.thoughtworks.xstream.XStream;
import org.xper.rfplot.drawing.GaborSpec;

public class IsoGaborSpec extends GaborSpec {
    public String type;

    public IsoGaborSpec(GaborSpec d, String colors) {
        super(d);
        this.type = colors;
    }



    public IsoGaborSpec() {
    }

    static {
        s = new XStream();
        s.alias("StimSpec", IsoGaborSpec.class);
        s.useAttributeFor("animation", boolean.class);
    }

    public String toXml() {
        return s.toXML(this);
    }

    public static IsoGaborSpec fromXml(String xml) {
        return (IsoGaborSpec)s.fromXML(xml);
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }
}
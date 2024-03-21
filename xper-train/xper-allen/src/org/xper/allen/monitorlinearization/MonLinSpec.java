package org.xper.allen.monitorlinearization;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.PngSpec;

public class MonLinSpec {
    RGBColor color;
    double angle = 0; // in degrees for the sinusoidal grating
    double gain=1;

    transient static XStream s;

    static {
        s = new XStream();
        s.alias("StimSpec", MonLinSpec.class);
    }

    public String toXml () {
        return s.toXML(this);
    }

    public static MonLinSpec fromXml (String xml) {
        MonLinSpec p = (MonLinSpec)s.fromXML(xml);
        return p;
    }
}
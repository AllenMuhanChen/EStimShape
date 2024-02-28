package org.xper.allen.monitorlinearization;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.PngSpec;

public class MonLinSpec {
    RGBColor color;

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
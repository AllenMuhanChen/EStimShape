package org.xper.allen.isoluminant;

import com.thoughtworks.xstream.XStream;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;

public class MixedGaborSpec {
    public IsoGaborSpec chromaticSpec;
    public GaborSpec luminanceSpec;
    String type;
    boolean animation;

    public MixedGaborSpec(IsoGaborSpec chromaticSpec, GaborSpec luminanceSpec, String colors) {
        this.chromaticSpec = chromaticSpec;
        this.luminanceSpec = luminanceSpec;
        this.type = colors;
        this.animation = false;
    }

    public MixedGaborSpec() {
    }

    protected static XStream s;
    static {
        s = new XStream();
        s.alias("StimSpec", MixedGaborSpec.class);
        s.useAttributeFor("animation", boolean.class);
    }

    public String toXml() {
        return s.toXML(this);
    }

    public static MixedGaborSpec fromXml(String xml) {
        return (MixedGaborSpec) s.fromXML(xml);
    }
}
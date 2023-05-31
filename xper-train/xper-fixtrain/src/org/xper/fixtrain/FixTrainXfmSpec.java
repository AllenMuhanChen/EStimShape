package org.xper.fixtrain;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import com.thoughtworks.xstream.XStream;

public class FixTrainXfmSpec {

    Coordinates2D translation;
    Coordinates2D scale;
    float rotation;
    RGBColor color;

    transient static XStream s;

    static FixTrainXfmSpec defaultXmlSpec;

    static {
        s = new XStream();
        s.alias("RFPlotXfmSpec", FixTrainXfmSpec.class);

        defaultXmlSpec = new FixTrainXfmSpec();
        defaultXmlSpec.setColor(new RGBColor(0f, 0f, 0f));
        defaultXmlSpec.setScale(new Coordinates2D(1.0, 1.0));
        defaultXmlSpec.setRotation(0f);
        defaultXmlSpec.setTranslation(new Coordinates2D(0, 0));
    }

    public String toXml () {
        return FixTrainXfmSpec.toXml(this);
    }

    public static String toXml (FixTrainXfmSpec spec) {
        return s.toXML(spec);
    }

    public static FixTrainXfmSpec fromXml (String xml) {
        if (xml == null) return defaultXmlSpec;

        FixTrainXfmSpec spec = (FixTrainXfmSpec)s.fromXML(xml);
        return spec;
    }

    public Coordinates2D getTranslation() {
        return translation;
    }

    public void setTranslation(Coordinates2D translation) {
        this.translation = translation;
    }

    public Coordinates2D getScale() {
        return scale;
    }

    public void setScale(Coordinates2D scale) {
        this.scale = scale;
    }

    public float getRotation() {
        return rotation;
    }

    public void setRotation(float rotation) {
        this.rotation = rotation;
    }

    public RGBColor getColor() {
        return color;
    }

    public void setColor(RGBColor color) {
        this.color = color;
    }
}
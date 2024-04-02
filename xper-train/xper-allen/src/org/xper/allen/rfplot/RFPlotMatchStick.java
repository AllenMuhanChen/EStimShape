package org.xper.allen.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.XMLizable;
import org.xper.utils.RGBColor;
import org.xper.rfplot.drawing.DefaultSpecRFPlotDrawable;

public class RFPlotMatchStick extends DefaultSpecRFPlotDrawable {
    AllenMatchStick matchStick;
    RFPlotMatchStickSpec spec;
    double sizeDiameterDegrees = 10;

    public RFPlotMatchStick() {
        setDefaultSpec();
    }

    @Override
    public void draw(Context context) {
        AllenMatchStick matchStick = new AllenMatchStick();
        matchStick.genMatchStickFromShapeSpec(spec.getMStickSpec(), spec.getRotation());
        matchStick.drawFast();
    }

    @Override
    public void setSpec(String spec) {
        this.spec = RFPlotMatchStickSpec.fromXml(spec);
    }

    @Override
    public void setDefaultSpec() {
        matchStick = new AllenMatchStick();
        matchStick.setProperties(sizeDiameterDegrees, "SHADE");
        matchStick.genMatchStickRand();
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick, false);

        this.spec = new RFPlotMatchStickSpec(spec,
                sizeDiameterDegrees,
                new RGBColor(1, 0, 0),
                new double[]{0, 0, 0}, "SHADE");


    }

    @Override
    public String getSpec() {
        return spec.toXml();
    }

    @Override
    public void projectCoordinates(Coordinates2D mouseCoordinates) {

    }

    public static class RFPlotMatchStickSpec implements XMLizable {
        public AllenMStickSpec spec;
        public double sizeDiameterDegrees;
        public RGBColor color;
        public double[] rotation;
        public String texture;

        public RFPlotMatchStickSpec(AllenMStickSpec spec, double sizeDiameterDegrees, RGBColor color, double[] rotation, String texture) {
            this.spec = spec;
            this.sizeDiameterDegrees = sizeDiameterDegrees;
            this.color = color;
            this.rotation = rotation;
            this.texture = texture;
        }

        public RFPlotMatchStickSpec(RFPlotMatchStickSpec other) {
            this.spec = other.spec;
            this.sizeDiameterDegrees = other.sizeDiameterDegrees;
            this.color = other.color;
            this.rotation = other.rotation;
            this.texture = other.texture;
        }

        public RFPlotMatchStickSpec() {
        }

        static XStream s;

        static {
            s = new XStream();
            s.alias("StimSpec", RFPlotMatchStickSpec.class);
            s.useAttributeFor("animation", boolean.class);
        }

        public String toXml() {
            return s.toXML(this);
        }

        public static RFPlotMatchStickSpec fromXml(String spec) {
            return (RFPlotMatchStickSpec) s.fromXML(spec);
        }

        public AllenMStickSpec getMStickSpec() {
            return spec;
        }

        public void setSpec(AllenMStickSpec spec) {
            this.spec = spec;
        }

        public void setSpec(AllenMatchStick matchStick) {
            this.spec = new AllenMStickSpec();
            this.spec.setMStickInfo(matchStick, false);
        }

        public double getSizeDiameterDegrees() {
            return sizeDiameterDegrees;
        }

        public void setSizeDiameterDegrees(double sizeDiameterDegrees) {
            this.sizeDiameterDegrees = sizeDiameterDegrees;
        }

        public RGBColor getColor() {
            return color;
        }

        public void setColor(RGBColor color) {
            this.color = color;
        }

        public double[] getRotation() {
            return rotation;
        }

        public void setRotation(double[] rotation) {
            this.rotation = rotation;
        }

        public String getTexture() {
            return texture;
        }

        public void setTexture(String texture) {
            this.texture = texture;
        }

        @Override
        public XMLizable getFromXml(String xml) {
            return fromXml(xml);
        }
    }
}
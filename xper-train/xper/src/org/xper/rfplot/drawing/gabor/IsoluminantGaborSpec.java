package org.xper.rfplot.drawing.gabor;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.GaborSpec;

public class IsoluminantGaborSpec extends GaborSpec {
    RGBColor color1;
    RGBColor color2;
    boolean modRedGreen;
    boolean modBlueYellow;

    public IsoluminantGaborSpec(RGBColor color1, RGBColor color2, boolean modRedGreen, boolean modBlueYellow, GaborSpec gaborSpec) {
        this.color1 = color1;
        this.color2 = color2;
        this.modRedGreen = modRedGreen;
        this.modBlueYellow = modBlueYellow;
        this.setFrequency(gaborSpec.getFrequency());
        this.setPhase(gaborSpec.getPhase());
        this.setSize(gaborSpec.getSize());
        this.setXCenter(gaborSpec.getXCenter());
        this.setYCenter(gaborSpec.getYCenter());
        this.setOrientation(gaborSpec.getOrientation());
        this.setAnimation(gaborSpec.isAnimation());
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


    public RGBColor getColor1() {
        return color1;
    }

    public void setColor1(RGBColor color1) {
        this.color1 = color1;
    }

    public RGBColor getColor2() {
        return color2;
    }

    public void setColor2(RGBColor color2) {
        this.color2 = color2;
    }

    public boolean isModRedGreen() {
        return modRedGreen;
    }

    public void setModRedGreen(boolean modRedGreen) {
        this.modRedGreen = modRedGreen;
    }

    public boolean isModBlueYellow() {
        return modBlueYellow;
    }

    public void setModBlueYellow(boolean modBlueYellow) {
        this.modBlueYellow = modBlueYellow;
    }

}
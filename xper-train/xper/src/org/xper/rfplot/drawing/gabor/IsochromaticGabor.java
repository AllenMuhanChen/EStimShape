package org.xper.rfplot.drawing.gabor;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.IsochromaticGaborSpec;

import java.awt.*;

public class IsochromaticGabor extends Gabor{

    IsochromaticGaborSpec gaborSpec;
    ColourConverter.WhitePoint whitePoint = ColourConverter.WhitePoint.D65;


    @Override
    protected float[] modulateColor(float modFactor) {
        // Convert RGB to Lab
        RGBColor color = gaborSpec.getColor();
        double [] lab = ColourConverter.getLab(new Color(color.getRed(), color.getGreen(), color.getBlue()), whitePoint);

        // Modulate the L component for brightness
        lab[0] = lab[0] * modFactor; // Ensure L stays within bounds

        // Convert back to RGB
        double[] modulatedRGB = ColourConverter.labToRGB(lab[0], lab[1], lab[2], whitePoint);

        // Return as an array for OpenGL
        float[] rgb = new float[3];
        //convert back to 0-1 scale
        rgb[0] = (float) (modulatedRGB[0]);
        rgb[1] = (float) (modulatedRGB[1]);
        rgb[2] = (float) (modulatedRGB[2]);

        return rgb;
    }

    @Override
    public IsochromaticGaborSpec getGaborSpec() {
        return gaborSpec;
    }

    public void setGaborSpec(IsochromaticGaborSpec gaborSpec) {
        this.gaborSpec = gaborSpec;
    }

    @Override
    public void setDefaultSpec() {
        setGaborSpec(new IsochromaticGaborSpec());
        getGaborSpec().setPhase(0);
        getGaborSpec().setFrequency(1);
        getGaborSpec().setOrientation(0);
        getGaborSpec().setAnimation(true);
        getGaborSpec().setSize(5);
        getGaborSpec().setXCenter(0);
        getGaborSpec().setYCenter(0);
        getGaborSpec().setColor(new RGBColor(1,1,1));
    }

    public String getSpec() {
        return getGaborSpec().toXml();
    }

    public void setSpec(String spec) {
        this.setGaborSpec(IsochromaticGaborSpec.fromXml(spec));
    }
}
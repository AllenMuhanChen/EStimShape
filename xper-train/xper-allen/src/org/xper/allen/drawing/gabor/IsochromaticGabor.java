package org.xper.allen.drawing.gabor;

import org.xper.drawing.RGBColor;

import java.awt.*;

public class IsochromaticGabor extends Gabor{

    RGBColor color;
    ColourConverter.WhitePoint whitePoint = ColourConverter.WhitePoint.D65;

    public IsochromaticGabor(RGBColor color) {
        this.color = color;
    }

    @Override
    protected float[] modulateColor(float modFactor) {
        // Convert RGB to Lab
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


}
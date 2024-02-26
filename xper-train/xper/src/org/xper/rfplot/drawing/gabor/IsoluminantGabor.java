package org.xper.rfplot.drawing.gabor;

import org.xper.drawing.RGBColor;

import java.awt.*;

public class IsoluminantGabor extends Gabor {

    RGBColor color1;
    RGBColor color2;
    boolean modRedGreen;
    boolean modBlueYellow;
    ColourConverter.WhitePoint whitePoint = ColourConverter.WhitePoint.D65;

    public IsoluminantGabor(RGBColor color1, RGBColor color2, boolean modRedGreen, boolean modBlueYellow) {
        this.color1 = color1;
        this.color2 = color2;
        this.modRedGreen = modRedGreen;
        this.modBlueYellow = modBlueYellow;
    }

    @Override
    protected float[] modulateColor(float modFactor) {
        // Ensure modFactor is within 0 and 1
        modFactor = Math.max(0, Math.min(modFactor, 1));

        // Convert both colors to Lab
        double[] lab1 = ColourConverter.getLab(new Color(color1.getRed(), color1.getGreen(), color1.getBlue()), whitePoint);
        double[] lab2 = ColourConverter.getLab(new Color(color2.getRed(), color2.getGreen(), color2.getBlue()), whitePoint);

        // Interpolate the a* and b* components between the two colors based on modFactor
        // Maintain constant L* (luminance) from the first color (or average them if you prefer)
        double L = lab1[0]; // or (lab1[0] + lab2[0]) / 2 for average luminance
        double a;
        double b;
        if (modRedGreen) {
            a = interpolate(lab1[1], lab2[1], modFactor);
        }
        else {
            a = lab1[1];
        }
        if (modBlueYellow)
            b = interpolate(lab1[2], lab2[2], modFactor);
        else
            b = lab1[2];

        // Convert the interpolated Lab color back to RGB
        double[] modulatedRGB = ColourConverter.labToRGB(L, a, b, whitePoint);

        // Return as an array for OpenGL
        float[] rgb = new float[3];
        rgb[0] = (float) (modulatedRGB[0]);
        rgb[1] = (float) (modulatedRGB[1]);
        rgb[2] = (float) (modulatedRGB[2]);

        return rgb;
    }

    private double interpolate(double value1, double value2, float factor) {
        return value1 + (value2 - value1) * factor;
    }
}
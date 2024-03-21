package org.xper.rfplot.drawing.gabor;

import org.xper.drawing.RGBColor;

public class GammaCorrection {
    public Gamma redGamma;
    public Gamma greenGamma;
    public Gamma blueGamma;

    public GammaCorrection(Gamma redGamma, Gamma greenGamma, Gamma blueGamma) {
        this.redGamma = redGamma;
        this.greenGamma = greenGamma;
        this.blueGamma = blueGamma;
    }

    public RGBColor correct(RGBColor color, double luminanceCandela) {
        RGBColor corrected = new RGBColor();
        corrected.setRed((float) redGamma.correct(color.getRed()*luminanceCandela));
        corrected.setGreen((float) greenGamma.correct(color.getGreen()*luminanceCandela));
        corrected.setBlue((float) blueGamma.correct(color.getBlue()*luminanceCandela));
        System.out.println("Corrected: r: " + corrected.getRed() + " g: " + corrected.getGreen() + " b: " + corrected.getBlue());
        return corrected;

    }

}
package org.xper.rfplot.drawing.gabor;

import org.apache.commons.math3.distribution.NormalDistribution;
import org.apache.commons.math3.optim.linear.LinearObjectiveFunction;
import org.xper.drawing.RGBColor;

import java.awt.*;

public class IsoluminantGabor extends Gabor {

    IsoluminantGaborSpec spec;
    ColourConverter.WhitePoint whitePoint = ColourConverter.WhitePoint.D65;

    double luminanceCandela = 200;

    GammaCorrection correction = new GammaCorrection(
            new Gamma(1168.883608034991, 2.493582260436006),
            new Gamma(1904.1406702103686, 2.4512161146614972),
            new Gamma(428.01063804554224, 2.277465659232506)
    );

    @Override
    protected float[] modulateColor(float modFactor) {
        // Ensure modFactor is within 0 and 1
        modFactor = Math.max(0, Math.min(modFactor, 1));

        double r=0;
        double g=0;
        double b=0;
        if (spec.modRedGreen) {
            r = interpolate(0, 1.0, modFactor);
            g = 1 - r;
            b = 0;
//            double rgRatio = Math.min(r,g) / Math.max(r,g);
//            double percentDecrease = .05 * (rgRatio);
//            if (rgRatio > 0.4) {
//                r = r * (1 - percentDecrease);
//                g = g * (1 - percentDecrease);
//            }

            System.out.println("r: " + r + " g: " + g + " b: " + b + "sum: " + (r+g+b));
        }
        else if (spec.modBlueYellow){
            r = interpolate(0, 0.5, modFactor);
            b = 0.5 - r;
            g = 0.5;
            System.out.println("r: " + r + " g: " + g + " b: " + b + "sum: " + (r+g+b));
        }

        // Gamma Correct (/ Linearize) the RGB based on the monitor
        RGBColor corrected = correction.correct(
                new RGBColor((float) r, (float) g, (float) b),
                luminanceCandela);
        // Return as an array for OpenGL
        float[] rgb = new float[3];
        rgb[0] = corrected.getRed();
        rgb[1] = corrected.getGreen();
        rgb[2] = corrected.getBlue();




        return rgb;
    }

    private double interpolate(double value1, double value2, float factor) {
        return value1 + (value2 - value1) * factor;
    }

    @Override
    public IsoluminantGaborSpec getGaborSpec() {
        return spec;
    }

    public void setGaborSpec(IsoluminantGaborSpec spec) {
        this.spec = spec;
    }

    @Override
    public void setDefaultSpec() {
        setGaborSpec(new IsoluminantGaborSpec());
        getGaborSpec().setPhase(0);
        getGaborSpec().setFrequency(0.01);
        getGaborSpec().setOrientation(0);
        getGaborSpec().setAnimation(true);
        getGaborSpec().setSize(89.99);
        getGaborSpec().setXCenter(0);
        getGaborSpec().setYCenter(0);
        getGaborSpec().setColor1(new RGBColor(0.5f, 0.5f, 0));
        getGaborSpec().setColor2(new RGBColor(0, 0.5f, 0.5f));
        getGaborSpec().setModRedGreen(true);
        getGaborSpec().setModBlueYellow(true);
    }

    public String getSpec() {
        return getGaborSpec().toXml();
    }

    public void setSpec(String spec) {
        recalculateTextureIfChangeSigma(spec);
        this.setGaborSpec(IsoluminantGaborSpec.fromXml(spec));
    }

    private void recalculateTextureIfChangeSigma(String spec) {
        String oldSpec = getSpec();
        IsoluminantGaborSpec oldGaborSpec = IsoluminantGaborSpec.fromXml(oldSpec);
        double oldSigma = oldGaborSpec.getSize();
        double newSigma = IsoluminantGaborSpec.fromXml(spec).getSize();
        if (oldSigma != newSigma) {
            recalculateTexture();
        }
    }
}
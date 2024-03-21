package org.xper.allen.isoluminant;

import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.Gabor;
import org.xper.rfplot.drawing.gabor.IsoluminantGaborSpec;

public class IsoluminantGabor extends Gabor {

    IsoluminantGaborSpec spec;
    double luminanceCandela;
    private LookUpTableCorrector lutCorrector;
    private SinusoidGainCorrector sinusoidGainCorrector;

    public IsoluminantGabor(IsoluminantGaborSpec spec, double luminanceCandela, LookUpTableCorrector lutCorrector, SinusoidGainCorrector sinusoidGainCorrector) {
        this.spec = spec;
        this.luminanceCandela = luminanceCandela;
        this.lutCorrector = lutCorrector;
        this.sinusoidGainCorrector = sinusoidGainCorrector;
    }

    @Override
    protected float[] modulateColor(float modFactor) {
        // Ensure modFactor is within 0 and 1
        modFactor = Math.max(0, Math.min(modFactor, 1));

        // get an angle of cosine out of the modFactor
        double angle = modFactor * 180;

        double gain;
        RGBColor corrected;
        if (spec.colors.equals("RedGreen")) {
            double luminanceRed = luminanceCandela * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceGreen = luminanceCandela * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            gain = sinusoidGainCorrector.getGain(Math.toDegrees(angle), "RedGreen");
            corrected = lutCorrector.correctRedGreen(luminanceRed * gain, luminanceGreen * gain);
        }
        else {
            throw new RuntimeException("Unknown color space: " + spec.colors);
        }




        return new float[]{corrected.getRed(), corrected.getGreen(), corrected.getBlue()};
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
    }


    public String getSpec() {
        return getGaborSpec().toXml();
    }


}
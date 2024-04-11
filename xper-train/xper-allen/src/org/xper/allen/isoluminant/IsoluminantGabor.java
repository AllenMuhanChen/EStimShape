package org.xper.allen.isoluminant;

import org.lwjgl.opengl.GL11;
import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.Context;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.gabor.Gabor;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

public class IsoluminantGabor extends Gabor {

    IsoGaborSpec spec;
    double luminanceCandela;
    private LookUpTableCorrector lutCorrector;
    private SinusoidGainCorrector sinusoidGainCorrector;

    public IsoluminantGabor(IsoGaborSpec spec, double luminanceCandela, LookUpTableCorrector lutCorrector, SinusoidGainCorrector sinusoidGainCorrector) {
        super();
        this.spec = spec;
        this.luminanceCandela = luminanceCandela;
        this.lutCorrector = lutCorrector;
        this.sinusoidGainCorrector = sinusoidGainCorrector;

        stepsPerHalfCycle = 100;
//        stepsPerHalfCycle = 25;
    }

    @Override
    protected float calcModFactor(float i, int STEPS) {
        return (float) Math.abs(((Math.abs(frequencyCyclesPerMm * (verticalPosition + phase))) % 1) * 2 - 1);
    }

    @Override
    protected float[] modulateColor(float modFactor) {
        // Ensure modFactor is within 0 and 1
        modFactor = Math.max(0, Math.min(modFactor, 1));

        // get an angle of cosine out of the modFactor
        double angle = modFactor * 180;

        double gain;
        RGBColor corrected;
        if (spec.type.equals("RedGreen")) {
            double luminanceRed = luminanceCandela * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceGreen = luminanceCandela * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            gain = sinusoidGainCorrector.getGain(angle, "RedGreen");
            corrected = lutCorrector.correctRedGreen(luminanceRed * gain, luminanceGreen * gain);
        }
        else if (spec.type.equals("CyanYellow")){
            double luminanceCyan = luminanceCandela * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceYellow = luminanceCandela * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            gain = sinusoidGainCorrector.getGain(angle, "CyanYellow");
            corrected = lutCorrector.correctCyanYellow(luminanceCyan * gain, luminanceYellow * gain);
        }
        else {
            throw new RuntimeException("Unknown color space: " + spec.type);
        }
        return new float[]{corrected.getRed(), corrected.getGreen(), corrected.getBlue()};
    }


    @Override
    public IsoGaborSpec getGaborSpec() {
        return spec;
    }

    public void setGaborSpec(IsoGaborSpec spec) {
        this.spec = spec;
    }

    @Override
    public void setDefaultSpec() {
    }

    public String getSpec() {
        return getGaborSpec().toXml();
    }

}
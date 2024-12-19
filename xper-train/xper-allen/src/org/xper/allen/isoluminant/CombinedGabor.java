package org.xper.allen.isoluminant;

import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.Gabor;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;

public class CombinedGabor extends Gabor {
    private final GaborSpec isochromaticSpec;
    double luminanceCandela;
    private final IsoGaborSpec isoluminantSpec;
    private final LookUpTableCorrector lutCorrector;
    private final SinusoidGainCorrector sinusoidGainCorrector;

    public CombinedGabor(IsoGaborSpec isoluminantSpec,
                         GaborSpec isochromaticSpec,
                         double luminanceCandela,
                         LookUpTableCorrector lutCorrector,
                         SinusoidGainCorrector sinusoidGainCorrector) {
        super();
        this.isoluminantSpec = isoluminantSpec;
        this.isochromaticSpec = isoluminantSpec;
        this.luminanceCandela = luminanceCandela;
        this.lutCorrector = lutCorrector;
        this.sinusoidGainCorrector = sinusoidGainCorrector;
    }

    @Override
    /**
     * convert the sinusoidal modulation factor to linear (angle), because sin gain modulator
     * takes angle as input
     */
    protected float calcModFactor(float i, int STEPS) {
        return (float) Math.abs(((Math.abs(frequencyCyclesPerMm * (verticalPosition + phase))) % 1) * 2 - 1);
    }

    @Override
    protected float[] modulateColor(float modFactor) {
        // Ensure modFactor is within 0 and 1
        modFactor = Math.max(0, Math.min(modFactor, 1));

        double min = 10;
        double max = 290;



        double targetCandela = modFactor * luminanceCandela;
        targetCandela = Math.max(min, Math.min(max, targetCandela));

        double angle = modFactor * 180;
        // get an angle of cosine out of the modFactor

        double gain;
        RGBColor corrected;
        if (isoluminantSpec.type.equals("RedGreen")) {
            double luminanceRed = targetCandela * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceGreen = targetCandela * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            gain = sinusoidGainCorrector.getGain(angle, "RedGreen");
            corrected = lutCorrector.correctRedGreen(luminanceRed * gain, luminanceGreen * gain);
        }
        else if (isoluminantSpec.type.equals("CyanYellow")){
            double luminanceCyan = targetCandela * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceYellow = targetCandela * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            gain = sinusoidGainCorrector.getGain(angle, "CyanYellow");
            corrected = lutCorrector.correctCyanYellow(luminanceCyan * gain, luminanceYellow * gain);
        }
        else {
            throw new RuntimeException("Unknown color space: " + isoluminantSpec.type);
        }
        return new float[]{corrected.getRed(), corrected.getGreen(), corrected.getBlue()};
    }





}
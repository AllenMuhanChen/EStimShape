package org.xper.allen.isoluminant;

import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.Gabor;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;

public class CombinedGabor extends Gabor {
    private final GaborSpec isochromaticSpec;
    private final IsoGaborSpec isoluminantSpec;
    private final LookUpTableCorrector lutCorrector;
    private final SinusoidGainCorrector sinusoidGainCorrector;
    private final double luminanceCandela;

    public CombinedGabor(IsoGaborSpec isoluminantSpec,
                         GaborSpec isochromaticSpec,
                         double luminanceCandela,
                         LookUpTableCorrector lutCorrector,
                         SinusoidGainCorrector sinusoidGainCorrector) {
        super();
        this.isoluminantSpec = isoluminantSpec;
        this.isochromaticSpec = isochromaticSpec;
        this.luminanceCandela = luminanceCandela;
        this.lutCorrector = lutCorrector;
        this.sinusoidGainCorrector = sinusoidGainCorrector;
    }

    protected float calcChromaticModFactor(float position) {
        double chromFreqCyclesPerMm = isoluminantSpec.getFrequency() / renderer.deg2mm(1);
        double chromPhase = renderer.deg2mm(isoluminantSpec.getPhase());
        return (float) Math.abs(((Math.abs(chromFreqCyclesPerMm * (position + chromPhase))) % 1) * 2 - 1);
    }

    protected float calcLuminanceModFactor(float position) {
        // Note: We need to handle isochromaticSpec's frequency separately since
        // frequencyCyclesPerMm is based on the current spec
        double lumFreqCyclesPerMm = isochromaticSpec.getFrequency() / renderer.deg2mm(1);
        double lumPhase = renderer.deg2mm(isochromaticSpec.getPhase());
        return (float) ((Math.cos(2 * Math.PI * lumFreqCyclesPerMm * (position + lumPhase)) + 1) / 2);
    }

    @Override
    protected float[] modulateColor(float modFactor) {
        // Calculate both chromatic and luminance modulation factors
        float chromaticModFactor = calcChromaticModFactor(verticalPosition);
        float luminanceModFactor = calcLuminanceModFactor(verticalPosition);

        // Ensure mod factors are within 0 and 1
        chromaticModFactor = Math.max(0, Math.min(chromaticModFactor, 1));
        luminanceModFactor = Math.max(0, Math.min(luminanceModFactor, 1));

        // Calculate base luminance level using luminance modulation
        double minLuminance = 10;
        double maxLuminance = 290;
        double targetCandela = luminanceModFactor * luminanceCandela;
        targetCandela = Math.max(minLuminance, Math.min(maxLuminance, targetCandela));

        // Calculate chromatic angle
        double angle = chromaticModFactor * 180;

        // Get color correction gain
        double gain;
        RGBColor corrected;

        if (isoluminantSpec.type.equals("RedGreen")) {
            double luminanceRed = targetCandela * (1 + Math.cos(Math.toRadians(angle))) / 2;
            double luminanceGreen = targetCandela * (1 + Math.cos(Math.toRadians(angle - 180))) / 2;
            gain = sinusoidGainCorrector.getGain(angle, "RedGreen");
            corrected = lutCorrector.correctRedGreen(luminanceRed * gain, luminanceGreen * gain);
        }
        else if (isoluminantSpec.type.equals("CyanYellow")) {
            double luminanceCyan = targetCandela * (1 + Math.cos(Math.toRadians(angle))) / 2;
            double luminanceYellow = targetCandela * (1 + Math.cos(Math.toRadians(angle - 180))) / 2;
            gain = sinusoidGainCorrector.getGain(angle, "CyanYellow");
            corrected = lutCorrector.correctCyanYellow(luminanceCyan * gain, luminanceYellow * gain);
        }
        else {
            throw new RuntimeException("Unknown color space: " + isoluminantSpec.type);
        }

        return new float[]{corrected.getRed(), corrected.getGreen(), corrected.getBlue()};
    }

    @Override
    public void setDefaultSpec() {
        // Not needed as we use both iso specs
    }

    @Override
    public IsoGaborSpec getGaborSpec() {
        return isoluminantSpec;
    }
}
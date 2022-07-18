package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NoiseChances;
import org.xper.allen.nafc.blockgen.SampleDistance;

public class PsychometricBlockGenParameters {
    private final int numPsychometricTrialsPerImage;
    private final int numRandTrials;
    private final NoiseChances noiseChances;
    private final SampleDistance sampleDistance;
    private final Lims choiceDistance;
    private final double sampleScale;
    private final double eyeWinSize;

    public PsychometricBlockGenParameters(int numPsychometricTrialsPerImage, int numRandTrials, NoiseChances noiseChances, SampleDistance sampleDistance, Lims choiceDistance, double sampleScale, double eyeWinSize) {
        this.numPsychometricTrialsPerImage = numPsychometricTrialsPerImage;
        this.numRandTrials = numRandTrials;
        this.noiseChances = noiseChances;
        this.sampleDistance = sampleDistance;
        this.choiceDistance = choiceDistance;
        this.sampleScale = sampleScale;
        this.eyeWinSize = eyeWinSize;
    }

    public int getNumPsychometricTrialsPerImage() {
        return numPsychometricTrialsPerImage;
    }

    public int getNumRandTrials() {
        return numRandTrials;
    }

    public NoiseChances getNoiseChances() {
        return noiseChances;
    }

    public SampleDistance getSampleDistance() {
        return sampleDistance;
    }

    public Lims getChoiceDistance() {
        return choiceDistance;
    }

    public double getSampleScale() {
        return sampleScale;
    }

    public double getEyeWinSize() {
        return eyeWinSize;
    }
}

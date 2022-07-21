package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.allen.nafc.blockgen.NumberOfDistractorsForPsychometricTrial;
import org.xper.allen.nafc.vo.NoiseParameters;

public class PsychometricTrialParameters extends NoisyTrialParameters{

    private NumberOfDistractorsForPsychometricTrial numDistractors;
    private PsychometricIds psychometricIds;

    public PsychometricTrialParameters(NoisyTrialParameters other, NumberOfDistractorsForPsychometricTrial numDistractors, PsychometricIds psychometricIds) {
        super(other);
        this.numDistractors = numDistractors;
        this.psychometricIds = psychometricIds;
    }

    public NumberOfDistractorsForPsychometricTrial getNumDistractors() {
        return numDistractors;
    }

    public void setNumDistractors(NumberOfDistractorsForPsychometricTrial numDistractors) {
        this.numDistractors = numDistractors;
    }

    public PsychometricIds getPsychometricIds() {
        return psychometricIds;
    }

    public void setPsychometricIds(PsychometricIds psychometricIds) {
        this.psychometricIds = psychometricIds;
    }
}

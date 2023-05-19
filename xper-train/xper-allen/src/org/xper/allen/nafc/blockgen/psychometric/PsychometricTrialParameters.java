package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.allen.nafc.blockgen.NumberOfDistractorsForPsychometricTrial;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.intan.stimulation.EStimParameters;

public class PsychometricTrialParameters extends NoisyTrialParameters{

    private NumberOfDistractorsForPsychometricTrial numDistractors;
    private PsychometricIds psychometricIds;
    private EStimParameters eStimParameters;

    public PsychometricTrialParameters(NoisyTrialParameters other, NumberOfDistractorsForPsychometricTrial numDistractors, PsychometricIds psychometricIds, EStimParameters eStimParameters) {
        super(other);
        this.numDistractors = numDistractors;
        this.psychometricIds = psychometricIds;
        this.eStimParameters = eStimParameters;
    }

    static{
        s.alias("PsychometricTrialParameters", PsychometricTrialParameters.class);
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

    public EStimParameters geteStimParameters() {
        return eStimParameters;
    }

    public void seteStimParameters(EStimParameters eStimParameters) {
        this.eStimParameters = eStimParameters;
    }
}
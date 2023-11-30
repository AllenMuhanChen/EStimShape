package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

public class ProceduralRandGenParameters {
    private final NAFCTrialParameters proceduralStimParameters;
    private final int numTrials;

    public ProceduralRandGenParameters(NAFCTrialParameters proceduralStimParameters, int numTrials) {
        this.proceduralStimParameters = proceduralStimParameters;
        this.numTrials = numTrials;
    }

    public ProceduralStim.ProceduralStimParameters getProceduralStimParameters() {
        return (ProceduralStim.ProceduralStimParameters) proceduralStimParameters;
    }

    public int getNumTrials() {
        return numTrials;
    }
}
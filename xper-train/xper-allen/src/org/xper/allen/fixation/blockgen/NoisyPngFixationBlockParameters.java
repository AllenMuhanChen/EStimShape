package org.xper.allen.fixation.blockgen;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseParameters;
import java.util.List;

public class NoisyPngFixationBlockParameters {
    NoisyPngFixationTrialParameters trialParams;
    int numTrials;

    public NoisyPngFixationBlockParameters(NoisyPngFixationTrialParameters trialParams, int numTrials) {
        this.trialParams = trialParams;
        this.numTrials = numTrials;
    }

    public NoisyPngFixationTrialParameters getTrialParams() {
        return trialParams;
    }

    public void setTrialParams(NoisyPngFixationTrialParameters trialParams) {
        this.trialParams = trialParams;
    }

    public int getNumTrials() {
        return numTrials;
    }

    public void setNumTrials(int numTrials) {
        this.numTrials = numTrials;
    }
}
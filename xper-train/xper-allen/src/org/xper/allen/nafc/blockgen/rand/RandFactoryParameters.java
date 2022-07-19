package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;

import java.util.List;

public class RandFactoryParameters {

    int numTrials;
    List<NumberOfDistractorsForRandTrial> numDistractors;
    List<NumberOfMorphCategories> numMorphs;
    List<NoisyTrialParameters> trialParameters;

    public RandFactoryParameters(int numTrials, List<NumberOfDistractorsForRandTrial> numDistractors, List<NumberOfMorphCategories> numMorphs, List<NoisyTrialParameters> trialParameters) {
        this.numTrials = numTrials;
        this.numDistractors = numDistractors;
        this.numMorphs = numMorphs;
        this.trialParameters = trialParameters;
    }

    public int getNumTrials() {
        return numTrials;
    }

    public void setNumTrials(int numTrials) {
        this.numTrials = numTrials;
    }

    public List<NumberOfDistractorsForRandTrial> getNumDistractors() {
        return numDistractors;
    }

    public void setNumDistractors(List<NumberOfDistractorsForRandTrial> numDistractors) {
        this.numDistractors = numDistractors;
    }

    public List<NumberOfMorphCategories> getNumMorphs() {
        return numMorphs;
    }

    public void setNumMorphs(List<NumberOfMorphCategories> numMorphs) {
        this.numMorphs = numMorphs;
    }

    public List<NoisyTrialParameters> getTrialParameters() {
        return trialParameters;
    }

    public void setTrialParameters(List<NoisyTrialParameters> trialParameters) {
        this.trialParameters = trialParameters;
    }
}

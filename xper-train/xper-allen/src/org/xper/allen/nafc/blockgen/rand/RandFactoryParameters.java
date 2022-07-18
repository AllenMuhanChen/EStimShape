package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.TypeFrequency;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;

public class RandFactoryParameters {

    int numTrials;
    TypeFrequency<NumberOfDistractorsForRandTrial> numDistractorsTypeFrequency;
    TypeFrequency<NumberOfMorphCategories> numMorphsTypeFrequency;
    TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency;

    public RandFactoryParameters(int numTrials, TypeFrequency<NumberOfDistractorsForRandTrial> numDistractorsTypeFrequency, TypeFrequency<NumberOfMorphCategories> numMorphsTypeFrequency, TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency) {
        this.numTrials = numTrials;
        this.numDistractorsTypeFrequency = numDistractorsTypeFrequency;
        this.numMorphsTypeFrequency = numMorphsTypeFrequency;
        this.trialParametersTypeFrequency = trialParametersTypeFrequency;
    }

    public int getNumTrials() {
        return numTrials;
    }

    public void setNumTrials(int numTrials) {
        this.numTrials = numTrials;
    }

    public TypeFrequency<NumberOfDistractorsForRandTrial> getNumDistractorsTypeFrequency() {
        return numDistractorsTypeFrequency;
    }

    public void setNumDistractorsTypeFrequency(TypeFrequency<NumberOfDistractorsForRandTrial> numDistractorsTypeFrequency) {
        this.numDistractorsTypeFrequency = numDistractorsTypeFrequency;
    }

    public TypeFrequency<NumberOfMorphCategories> getNumMorphsTypeFrequency() {
        return numMorphsTypeFrequency;
    }

    public void setNumMorphsTypeFrequency(TypeFrequency<NumberOfMorphCategories> numMorphsTypeFrequency) {
        this.numMorphsTypeFrequency = numMorphsTypeFrequency;
    }

    public TypeFrequency<NoisyTrialParameters> getTrialParametersTypeFrequency() {
        return trialParametersTypeFrequency;
    }

    public void setTrialParametersTypeFrequency(TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency) {
        this.trialParametersTypeFrequency = trialParametersTypeFrequency;
    }
}

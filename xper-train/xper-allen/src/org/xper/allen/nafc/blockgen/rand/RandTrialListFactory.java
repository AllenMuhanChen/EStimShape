package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.nafc.blockgen.TrialListFactory;
import org.xper.allen.nafc.blockgen.TypeFrequency;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;

import java.util.LinkedList;
import java.util.List;

public class RandTrialListFactory implements TrialListFactory {

    AbstractPsychometricTrialGenerator generator;
    int numTrials;
    TypeFrequency<NumberOfDistractorsForRandTrial> numDistractorsTypeFrequency;
    TypeFrequency<NumberOfMorphCategories> numMorphCategoriesTypeFrequency;
    TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency;

    public RandTrialListFactory(AbstractPsychometricTrialGenerator generator, int numTrials, TypeFrequency<NumberOfDistractorsForRandTrial> numDistractorsTypeFrequency, TypeFrequency<NumberOfMorphCategories> numMorphCategoriesTypeFrequency, TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency) {
        this.generator = generator;
        this.numTrials = numTrials;
        this.numDistractorsTypeFrequency = numDistractorsTypeFrequency;
        this.numMorphCategoriesTypeFrequency = numMorphCategoriesTypeFrequency;
        this.trialParametersTypeFrequency = trialParametersTypeFrequency;
    }

    @Override
    public List<Trial> createTrials() {
        List<NumberOfDistractorsForRandTrial> numDistractors = numDistractorsTypeFrequency.getTrialList(numTrials);
        List<NumberOfMorphCategories> numMorphCategories = numMorphCategoriesTypeFrequency.getTrialList(numTrials);
        List<NoisyTrialParameters> trialParameters = trialParametersTypeFrequency.getTrialList(numTrials);

        List<Trial> trials = new LinkedList<>();
        for(int i=0; i<numTrials; i++){
            RandNoisyTrialParameters randNoisyTrialParameters = new RandNoisyTrialParameters(numDistractors.get(i), numMorphCategories.get(i), trialParameters.get(i));
            trials.add(new RandTrial(generator, randNoisyTrialParameters));
        }
        return trials;
    }
}

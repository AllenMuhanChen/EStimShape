package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.nafc.blockgen.TrialListFactory;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;

import java.util.LinkedList;
import java.util.List;

public class RandTrialListFactory implements TrialListFactory {

    AbstractPsychometricTrialGenerator generator;
    RandFactoryParameters parameters;


    public RandTrialListFactory(AbstractPsychometricTrialGenerator generator, RandFactoryParameters parameters) {
        this.generator = generator;
        this.parameters = parameters;
        numTrials = parameters.numTrials;
        numDistractors = parameters.getNumDistractors();
        numMorphCategories = parameters.getNumMorphs();
        trialParameters = parameters.getTrialParameters();
    }

    int numTrials;
    List<NumberOfDistractorsForRandTrial> numDistractors;
    List<NumberOfMorphCategories> numMorphCategories;
    List<NoisyTrialParameters> trialParameters;



    @Override
    public List<Trial> createTrials() {
        List<NumberOfDistractorsForRandTrial> numDistractors = this.numDistractors;
        List<NumberOfMorphCategories> numMorphCategories = this.numMorphCategories;
        List<NoisyTrialParameters> trialParameters = this.trialParameters;

        List<Trial> trials = new LinkedList<>();
        for(int i=0; i<numTrials; i++){
            RandNoisyTrialParameters randNoisyTrialParameters = new RandNoisyTrialParameters(numDistractors.get(i), numMorphCategories.get(i), trialParameters.get(i));
            trials.add(new RandTrial(generator, randNoisyTrialParameters));
        }
        return trials;
    }
}

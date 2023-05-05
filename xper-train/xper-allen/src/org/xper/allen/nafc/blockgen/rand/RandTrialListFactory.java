package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.Stim;
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
    public List<Stim> createTrials() {
        List<NumberOfDistractorsForRandTrial> numDistractors = this.numDistractors;
        List<NumberOfMorphCategories> numMorphCategories = this.numMorphCategories;
        List<NoisyTrialParameters> trialParameters = this.trialParameters;

        List<Stim> stims = new LinkedList<>();
        for(int i=0; i<numTrials; i++){
            RandNoisyTrialParameters randNoisyTrialParameters = new RandNoisyTrialParameters(numDistractors.get(i), numMorphCategories.get(i), trialParameters.get(i));
            stims.add(new RandStim(generator, randNoisyTrialParameters));
        }
        return stims;
    }
}

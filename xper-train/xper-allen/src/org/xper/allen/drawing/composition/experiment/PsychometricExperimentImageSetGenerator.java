package org.xper.allen.drawing.composition.experiment;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;

public class PsychometricExperimentImageSetGenerator {

    @Dependency
    AbstractPsychometricTrialGenerator trialGenerator;

    public void generate(String pathToBaseStimulus){
        TwoByTwoMatchStick baseMatchStick = new TwoByTwoMatchStick(new GaussianNoiseMapper());
        baseMatchStick.setProperties(trialGenerator.getImageDimensionsDegrees(), "SHADE", 1.0);
        baseMatchStick.genMatchStickFromFile(pathToBaseStimulus, new double[]{0,0,0});

        while(true){

        }


    }
}
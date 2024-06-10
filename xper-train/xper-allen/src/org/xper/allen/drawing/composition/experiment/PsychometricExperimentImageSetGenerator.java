package org.xper.allen.drawing.composition.experiment;

import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;

public class PsychometricExperimentImageSetGenerator {

    @Dependency
    AbstractPsychometricTrialGenerator trialGenerator;

    public void generate(String pathToBaseStimulus){
        TwobyTwoMatchStick baseMatchStick = new TwobyTwoMatchStick();
        baseMatchStick.setProperties(trialGenerator.getImageDimensionsDegrees(), "SHADE");
        baseMatchStick.genMatchStickFromFile(pathToBaseStimulus, new double[]{0,0,0});

        while(true){

        }


    }
}
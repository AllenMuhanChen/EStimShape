package org.xper.allen.drawing.composition.experiment;

import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;

public class PsychometricExperimentImageSetGenerator {

    @Dependency
    AbstractPsychometricTrialGenerator trialGenerator;

    public void generate(String pathToBaseStimulus){
        ExperimentMatchStick baseMatchStick = new ExperimentMatchStick();
        baseMatchStick.setProperties(trialGenerator.getMaxImageDimensionDegrees());
        baseMatchStick.genMatchStickFromFile(pathToBaseStimulus, new double[]{0,0,0});

        while(true){

        }


    }
}
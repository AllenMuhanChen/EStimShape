package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.app.procedural.EStimExperimentTrialGenerator;
import org.xper.allen.nafc.blockgen.procedural.EStimShapeProceduralStim;

public class EStimShapeTwoByTwoProceduralMatchStick extends EStimShapeProceduralStim {
    public EStimShapeTwoByTwoProceduralMatchStick(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, int morphComponentIndex, boolean isEStimEnabled) {
        super(generator, parameters, baseMatchStick, morphComponentIndex, isEStimEnabled);
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
//        while (true) {
//            System.out.println("Trying to generate EStimShapeDeltaStim");
//            try {
//                EStimShapeProceduralMatchStick sample = generateSample();
//
//                assignDrivingAndDeltaIndices(sample);
//
//                generateMatch(sample);
//
//                generateProceduralDistractors(sample);
//
//                generateRandDistractors();
//
//                break;
//            } catch (ProceduralMatchStick.MorphRepetitionException mre){
//                System.out.println(mre.getMessage());
//            }
//        }
    }
}
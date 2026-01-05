package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.nafc.NAFCStim;

import java.util.LinkedList;
import java.util.List;

public class EStimExperimentVariantsDeltaGenType extends EStimExperimentVariantsGenType{

    public String getLabel() {
        return "EStimExperimentDeltaVariants";
    }

    @Override
    protected List<NAFCStim> genTrials(EStimExperimentGenType.EStimExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<>();

        int morphIndex = parameters.compId;
        int noiseIndex = morphIndex;

        //use that trial's base matchstick to generate the rest of the trials
        for (int i = 0; i < parameters.getNumTrials(); i++) {
            if (parameters.stimId == 0){
                newBlock.add(EStimShapeVariantsDeltaNAFCStim.createSampledDeltaNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        false,
                        parameters.isEStimEnabled));

                newBlock.add(EStimShapeVariantsDeltaNAFCStim.createSampledDeltaNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        true,
                        parameters.isEStimEnabled));
            } else {
                //using estim value from the GUI field
                EStimShapeVariantsNAFCStim stim = new EStimShapeVariantsDeltaNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        parameters.stimId,
                        false,
                        parameters.isEStimEnabled);
                newBlock.add(stim);

                EStimShapeVariantsNAFCStim deltaStim = new EStimShapeVariantsDeltaNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        parameters.stimId,
                        true,
                        parameters.isEStimEnabled);
                newBlock.add(deltaStim);
            }
        }
        return newBlock;
    }
}

package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.procedural.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.util.AllenDbUtil;

public class EStimProceduralStim extends ProceduralStim{
    public EStimProceduralStim(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, int morphComponentIndex, int noiseComponentIndex) {
        super(generator, parameters, baseMatchStick, morphComponentIndex);
    }

    @Override
    public void writeStim() {
        writeStimObjDataSpecs();
        assignTaskId();
        writeStimSpec();
        writeEStimSpec();
    }

    @Override
    protected ProceduralMatchStick generateSample() {
        while (true) {
            //Generate Sample
            EStimShapeProceduralMatchStick sample = new EStimShapeProceduralMatchStick(
                    RFStrategy.PARTIALLY_INSIDE,
                    ((EStimExperimentTrialGenerator) generator).getRF()
            );
            sample.setProperties(parameters.getSize(), parameters.textureType);
            sample.setStimColor(parameters.color);
            try {
                sample.genMatchStickFromComponentInNoise(baseMatchStick, morphComponentIndex, 0);
            } catch (ProceduralMatchStick.MorphRepetitionException e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
                continue;
            }

            mSticks.setSample(sample);
            mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));
            return sample;
        }
    }

    protected void writeEStimSpec() {
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeEStimObjData(getStimId(), "EStimEnabled", "");
    }

    @Override
    protected void writeStimSpec(){
        // Only reward for choosing the correct, or procedural distractor, not a random distractor.
        int numProceduralDistractors = this.parameters.numChoices - this.parameters.numRandDistractors - 1;
        int[] rewardList = new int[numProceduralDistractors + 1];
        rewardList[0] = 0; //match
        for (int i = 1; i <= numProceduralDistractors; i++) { //procedural distractors
            rewardList[i] = i;
        }

        NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
                getStimId(),
                (AllenDbUtil) generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds, RewardPolicy.LIST, rewardList);

        stimSpecWriter.writeStimSpec();
    }
}
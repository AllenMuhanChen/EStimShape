package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.util.AllenDbUtil;

public class EStimProceduralStim extends ProceduralStim{
    public EStimProceduralStim(NAFCBlockGen generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, int morphComponentIndex, int noiseComponentIndex) {
        super(generator, parameters, baseMatchStick, morphComponentIndex);
    }


    @Override
    public void writeStim() {
        writeStimObjDataSpecs();
        assignTaskId();
        writeStimSpec();
        writeEStimSpec();
    }

    protected void writeEStimSpec() {
        AllenDbUtil dbUtil = (AllenDbUtil) generator.getDbUtil();
        dbUtil.writeEStimObjData(getStimId(), "EStimEnabled", "");
    }

    @Override
    protected void writeStimSpec(){
//        //Only reward correct choice.
//        NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
//                getStimId(),
//                (AllenDbUtil) generator.getDbUtil(),
//                parameters,
//                coords,
//                parameters.numChoices,
//                stimObjIds, RewardPolicy.LIST, new int[]{0});

        // Only reward for choosing the correct, or procedural distractor, not a random distractor.
        int numProceduralDitractors = this.parameters.numChoices - this.parameters.numRandDistractors - 1;
        int[] rewardList = new int[numProceduralDitractors + 1];
        rewardList[0] = 0; //match
        for (int i = 1; i <= numProceduralDitractors; i++) { //procedural distractors
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
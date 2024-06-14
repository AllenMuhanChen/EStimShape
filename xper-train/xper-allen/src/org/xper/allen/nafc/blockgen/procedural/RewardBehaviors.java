package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.experiment.RewardPolicy;

public class RewardBehaviors {
    public static RewardBehavior rewardMatchOnly() {
        RewardPolicy rewardPolicy = RewardPolicy.LIST;
        int[] rewardList = {0};
        return new RewardBehavior(rewardPolicy, rewardList);
    }

    public static RewardBehavior rewardAnyChoice() {
        int[] rewardList = new int[0];

        RewardPolicy rewardPolicy = RewardPolicy.ANY;
        return new RewardBehavior(rewardPolicy, rewardList);
    }

    public static RewardBehavior rewardReasonableChoicesOnly(ProceduralStim.ProceduralStimParameters parameters) {
        // Only reward for choosing the correct, or procedural distractor, not a random distractor.
        int numProceduralDistractors = parameters.numChoices - parameters.numRandDistractors - 1;
        int[] rewardList = new int[numProceduralDistractors + 1];
        rewardList[0] = 0; //match
        for (int i = 1; i <= numProceduralDistractors; i++) { //procedural distractors
            rewardList[i] = i;
        }

        RewardPolicy rewardPolicy = RewardPolicy.LIST;
        return new RewardBehavior(rewardPolicy, rewardList);
    }
}
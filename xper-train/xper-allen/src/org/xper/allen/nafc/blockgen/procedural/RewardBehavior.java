package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.experiment.RewardPolicy;

public class RewardBehavior {
    public final int[] rewardList;
    public final RewardPolicy rewardPolicy;

    public RewardBehavior(RewardPolicy rewardPolicy, int[] rewardList) {
        this.rewardList = rewardList;
        this.rewardPolicy = rewardPolicy;
    }
}
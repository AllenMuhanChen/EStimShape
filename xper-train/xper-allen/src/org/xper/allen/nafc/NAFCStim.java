package org.xper.allen.nafc;

import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.allen.nafc.blockgen.procedural.RewardBehavior;

public interface NAFCStim extends Stim{
    RewardBehavior specifyRewardBehavior();

    public NAFCTrialParameters getParameters();
}
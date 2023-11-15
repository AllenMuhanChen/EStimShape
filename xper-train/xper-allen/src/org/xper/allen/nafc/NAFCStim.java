package org.xper.allen.nafc;

import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

public interface NAFCStim extends Stim{
    public NAFCTrialParameters getParameters();
}
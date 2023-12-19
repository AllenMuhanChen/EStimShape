package org.xper.allen.fixation.blockgen;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.vo.NoiseParameters;

import java.util.List;

public class NoisyPngFixationBlockGen extends AbstractMStickPngTrialGenerator {

    private NoisyPngFixationBlockParameters params;

    public void setUp(NoisyPngFixationBlockParameters params) {
        this.params = params;
    }

    @Override
    protected void addTrials() {
        for (int i = 0; i < params.getNumTrials(); i++) {
            getStims().add(new NoisyPngFixationStim(this, params.getTrialParams()));
        }
    }
}
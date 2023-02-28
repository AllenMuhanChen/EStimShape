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
        List<NoiseParameters> noises = params.getNoiseParameters();
        for (NoiseParameters noise : noises) {
            NoisyPngFixationTrialParameters trialParams = new NoisyPngFixationTrialParameters(noise, params.getDistanceLims(), params.getSize());
            stims.add(new NoisyPngFixationStim(this, trialParams));
        }
    }



}

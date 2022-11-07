package org.xper.allen.fixation.blockgen;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.Trial;

import java.util.LinkedList;
import java.util.List;

public class NoisyPngFixationBlockGen extends AbstractMStickPngTrialGenerator {

    private NoisyPngFixationParameters params;
    private double numTrials;

    public NoisyPngFixationBlockGen(NoisyPngFixationParameters params, double numTrials) {
        this.params = params;
        this.numTrials = numTrials;
    }

    @Override
    protected void addTrials() {
        List<Trial> trials = new LinkedList<>();

        for(int i = 0; i< numTrials; i++){
            trials.add(new NoisyPngFixationTrial(this, params));
        }
    }



}

package org.xper.allen.nafc.blockgen.procedural;

import java.util.LinkedList;
import java.util.List;

public class RandStimModel {
    public static final String label = "Rand";

    protected ProceduralExperimentBlockGen generator;

    public RandStimModel(ProceduralExperimentBlockGen generator) {
        this.generator = generator;
    }

    public List<ProceduralStim> genTrials(ProceduralStim.ProceduralStimParameters proceduralStimParameters, int numTrials) {
        List<ProceduralStim> newBlock = new LinkedList<>();
        for (int i = 0; i < numTrials; i++) {
            ProceduralStim stim = new ProceduralRandStim(generator, proceduralStimParameters);
            newBlock.add(stim);
        }
        return newBlock;
    }
}
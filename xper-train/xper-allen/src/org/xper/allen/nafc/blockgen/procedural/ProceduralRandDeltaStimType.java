package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.NAFCStim;

import java.util.LinkedList;
import java.util.List;

public class ProceduralRandDeltaStimType extends ProceduralRandGenType{

    public ProceduralRandDeltaStimType(NAFCBlockGen generator) {
        super(generator);
    }

    @Override
    protected List<NAFCStim> genTrials(GenParameters genParameters) {
        List<NAFCStim> newBlock = new LinkedList<>();
        for (int i = 0; i < genParameters.getNumTrials(); i++) {
            ProceduralStim stim = new ProceduralRandStimDeltaNoise(generator, (ProceduralStim.ProceduralStimParameters) genParameters.getProceduralStimParameters());
            newBlock.add(stim);
        }
        return newBlock;
    }

    public String getLabel() {
        return "RandDeltaProcedural";
    }
}
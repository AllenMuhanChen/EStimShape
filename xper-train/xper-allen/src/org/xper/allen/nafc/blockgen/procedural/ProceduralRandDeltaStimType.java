package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.NAFCStim;

import java.util.LinkedList;
import java.util.List;

public class ProceduralRandDeltaStimType extends ProceduralRandGenType{
    public static final String label= "RandDeltaProcedural";

    public ProceduralRandDeltaStimType(NAFCBlockGen generator) {
        super(generator);
    }

    @Override
    protected List<NAFCStim> genTrials(ProceduralRandGenParameters proceduralRandGenParameters) {
        List<NAFCStim> newBlock = new LinkedList<>();
        for (int i = 0; i < proceduralRandGenParameters.getNumTrials(); i++) {
            ProceduralStim stim = new ProceduralRandStimDeltaNoise(generator, (ProceduralStim.ProceduralStimParameters) proceduralRandGenParameters.getProceduralStimParameters());
            newBlock.add(stim);
        }
        return newBlock;
    }

    @Override
    public String getLabel(){
        return label;
    }
}
package org.xper.allen.nafc.blockgen;

import org.xper.allen.drawing.composition.noisy.NoisePositions;
import org.xper.allen.nafc.vo.NoiseForm;
import org.xper.allen.nafc.vo.NoiseType;

public class NoiseFormer {

    private static NoisePositions noisePositions;

    public static NoiseForm getNoiseForm(NoiseType noiseType){
        if(noiseType == NoiseType.NONE){
            noisePositions = new NoisePositions(0.0,0.0);
        }
        else if(noiseType == NoiseType.PRE_JUNC){
            noisePositions = new NoisePositions(0.6, 0.9);
        }
        else{
            noisePositions = new NoisePositions(1.0,1.3);
        }

        return new NoiseForm(noiseType, noisePositions);
    }
}

package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;

import java.util.LinkedList;
import java.util.List;

public class ProceduralRandStimDeltaNoise extends ProceduralRandStim {
    public ProceduralRandStimDeltaNoise(NAFCBlockGen generator, ProceduralStimParameters parameters) {
        super(generator, parameters);
    }

    @Override
    protected void chooseMorphAndNoiseComponents() {
        morphComponentIndex = baseMatchStick.chooseRandLeaf();
        //any random component except the morph component
        do {
            noiseComponentIndex = baseMatchStick.chooseRandLeaf();
            System.out.println("Morph Component Index: " + morphComponentIndex);
            System.out.println("Noise Component Index: " + noiseComponentIndex);
        } while (noiseComponentIndex == morphComponentIndex);
    }

    @Override
    protected void writeStimSpec(){
        NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
                ProceduralRandDeltaStimType.label,
                getTaskId(),
                generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds);

        stimSpecWriter.writeStimSpec();

    }
}
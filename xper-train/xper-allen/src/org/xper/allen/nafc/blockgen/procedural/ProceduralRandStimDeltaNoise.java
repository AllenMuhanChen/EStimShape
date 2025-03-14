package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.util.AllenDbUtil;

public class ProceduralRandStimDeltaNoise extends ProceduralRandStim {
    public ProceduralRandStimDeltaNoise(NAFCBlockGen generator, ProceduralStimParameters parameters) {
        super(generator, parameters);
    }


    protected void chooseMorphComponent() {
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
        NAFCStimSpecWriter stimSpecWriter = NAFCStimSpecWriter.createForNoEStim(
                new ProceduralRandDeltaStimType(generator).getLabel(),
                getStimId(),
                (AllenDbUtil) generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds, RewardPolicy.LIST, new int[]{0});

        stimSpecWriter.writeStimSpec();

    }
}
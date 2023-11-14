package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ExperimentMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;

public class ProceduralRandStim extends ProceduralStim{
    public static final int MAX_TRIES = 10;
    public ProceduralRandStim(ProceduralExperimentBlockGen generator, ProceduralStim.ProceduralStimParameters parameters) {
        super(generator, parameters, new ProceduralMatchStick(), 0);
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while (true) {
            try {
                baseMatchStick = genRandBaseMStick();
                baseMatchStick.setMaxAttempts(MAX_TRIES);
                drivingComponent = baseMatchStick.chooseRandLeaf();
                super.generateMatchSticksAndSaveSpecs();
                break;
            } catch (MorphedMatchStick.MorphException me) {
                System.out.println("MorphException: " + me.getMessage());
            }
        }

    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(generator.getMaxImageDimensionDegrees());
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();
        return baseMStick;
    }
}
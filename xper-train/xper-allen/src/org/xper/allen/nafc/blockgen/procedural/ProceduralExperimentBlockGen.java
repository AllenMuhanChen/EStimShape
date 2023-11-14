package org.xper.allen.nafc.blockgen.procedural;

import org.xper.Dependency;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class ProceduralExperimentBlockGen extends AbstractMStickPngTrialGenerator<ProceduralStim> {

    @Dependency
    String generatorNoiseMapPath;

    @Dependency
    String experimentNoiseMapPath;

    public void addRandTrainTrials(ProceduralStim.ProceduralStimParameters proceduralStimParameters, int numTrials){

        for(int i=0; i<numTrials; i++){
            ProceduralMatchStick baseMStick = genRandBaseMStick();
            int drivingComp = baseMStick.chooseRandLeaf();
            ProceduralStim stim = new ProceduralStim(this, proceduralStimParameters, baseMStick, drivingComp);

            getStims().add(stim);
        }

    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(getMaxImageDimensionDegrees());
        baseMStick.genMatchStickRand();
        return baseMStick;
    }

    @Override
    protected void addTrials() {

    }

    public String getGeneratorNoiseMapPath() {
        return generatorNoiseMapPath;
    }

    public void setGeneratorNoiseMapPath(String generatorNoiseMapPath) {
        this.generatorNoiseMapPath = generatorNoiseMapPath;
    }

    public String getExperimentNoiseMapPath() {
        return experimentNoiseMapPath;
    }

    public void setExperimentNoiseMapPath(String experimentNoiseMapPath) {
        this.experimentNoiseMapPath = experimentNoiseMapPath;
    }
}
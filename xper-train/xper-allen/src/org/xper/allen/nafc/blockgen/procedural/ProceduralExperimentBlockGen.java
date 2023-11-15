package org.xper.allen.nafc.blockgen.procedural;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class ProceduralExperimentBlockGen extends AbstractMStickPngTrialGenerator<ProceduralStim> {

    @Dependency
    String generatorNoiseMapPath;

    @Dependency
    String experimentNoiseMapPath;

    List<List<ProceduralStim>> stimBlocks = new LinkedList<>();

    public void removeBlock(int blockIndex){
        stimBlocks.remove(blockIndex);
    }

    public void addRandTrainTrials(ProceduralStim.ProceduralStimParameters proceduralStimParameters, int numTrials){
        List<ProceduralStim> newBlock = new LinkedList<>();
        for(int i=0; i<numTrials; i++){
            ProceduralStim stim = new ProceduralRandStim(this, proceduralStimParameters);
            newBlock.add(stim);
        }
        stimBlocks.add(newBlock);
    }

    public void editRandTrainTrials(ProceduralStim.ProceduralStimParameters proceduralStimParameters, int numTrials, int blockIndex){
        stimBlocks.get(blockIndex).clear();
        for(int i=0; i<numTrials; i++){
            ProceduralStim stim = new ProceduralRandStim(this, proceduralStimParameters);
            stimBlocks.get(blockIndex).add(stim);
        }
    }

    public void addMockTrainTrials(ProceduralStim.ProceduralStimParameters proceduralStimParameters, int numTrials){
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(getMaxImageDimensionDegrees());
        baseMStick.setStimColor(proceduralStimParameters.color);
        baseMStick.genMatchStickRand();
        int drivingComponent = baseMStick.chooseRandLeaf();
        for(int i=0; i<numTrials; i++){
            ProceduralStim stim = new ProceduralStim(this, proceduralStimParameters, baseMStick, drivingComponent);
            getStims().add(stim);
        }
    }


    @Override
    protected void addTrials() {
        getStims().clear();
        for (List<ProceduralStim> stimBlock : stimBlocks) {
            getStims().addAll(stimBlock);
        }
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
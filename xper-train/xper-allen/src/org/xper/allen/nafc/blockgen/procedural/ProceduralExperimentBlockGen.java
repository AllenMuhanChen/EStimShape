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

    public void addBlock(int blockIndex, List<ProceduralStim> block){
        stimBlocks.add(blockIndex, block);
    }

    public void addBlock(List<ProceduralStim> block){
        stimBlocks.add(block);
    }

    public void editBlock(int blockIndex, List<ProceduralStim> block){
        stimBlocks.set(blockIndex, block);
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

    public ProceduralStim.ProceduralStimParameters getBlockParameters(int blockIndex) {
        if (blockIndex >= 0 && blockIndex < stimBlocks.size()) {
            List<ProceduralStim> block = stimBlocks.get(blockIndex);
            if (!block.isEmpty()) {
                ProceduralStim firstStim = block.get(0);
                return firstStim.parameters; // Assuming ProceduralStim has a method to get its parameters
            }
        }
        return null; // or throw an exception if the index is out of bounds or the block is empty
    }

    public int getNumTrials(int selectedIndex) {
        if (selectedIndex >= 0 && selectedIndex < stimBlocks.size()) {
            List<ProceduralStim> block = stimBlocks.get(selectedIndex);
            return block.size();
        }
        return 0; // or throw an exception if the index is out of bounds
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
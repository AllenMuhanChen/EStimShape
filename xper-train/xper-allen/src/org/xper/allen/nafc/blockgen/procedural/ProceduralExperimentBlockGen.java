package org.xper.allen.nafc.blockgen.procedural;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

import java.util.LinkedList;
import java.util.List;

public class ProceduralExperimentBlockGen extends AbstractMStickPngTrialGenerator<Stim> {

    @Dependency
    String generatorNoiseMapPath;

    @Dependency
    String experimentNoiseMapPath;

    List<List<NAFCStim>> stimBlocks = new LinkedList<List<NAFCStim>>();


    public void removeBlock(int blockIndex){
        stimBlocks.remove(blockIndex);
    }

    public void addBlock(int blockIndex, List<NAFCStim> block){
        stimBlocks.add(blockIndex, block);
    }

    public void addBlock(List<NAFCStim> block){
        stimBlocks.add(block);
    }

    public void editBlock(int blockIndex, List<NAFCStim> block){
        stimBlocks.set(blockIndex, block);
    }

    public List<NAFCStim> getBlock(int blockIndex){
        return stimBlocks.get(blockIndex);
    }

    public NAFCTrialParameters getBlockParameters(int blockIndex) {
        if (blockIndex >= 0 && blockIndex < stimBlocks.size()) {
            List<NAFCStim> block = stimBlocks.get(blockIndex);
            if (!block.isEmpty()) {
                NAFCStim firstStim = block.get(0);
                return firstStim.getParameters(); // Assuming ProceduralStim has a method to get its parameters
            }
        }
        return null; // or throw an exception if the index is out of bounds or the block is empty
    }

    public int getNumTrials(int selectedIndex) {
        if (selectedIndex >= 0 && selectedIndex < stimBlocks.size()) {
            List<NAFCStim> block = stimBlocks.get(selectedIndex);
            return block.size();
        }
        return 0; // or throw an exception if the index is out of bounds
    }

    @Override
    protected void addTrials() {
        getStims().clear();
        for (List<NAFCStim> stimBlock : stimBlocks) {
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
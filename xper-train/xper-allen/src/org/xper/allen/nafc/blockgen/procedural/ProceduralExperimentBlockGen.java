package org.xper.allen.nafc.blockgen.procedural;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class ProceduralExperimentBlockGen extends AbstractMStickPngTrialGenerator<Stim> {

    @Dependency
    String generatorNoiseMapPath;

    @Dependency
    String experimentNoiseMapPath;

    List<List<NAFCStim>> stimBlocks = new LinkedList<List<NAFCStim>>();
    Map<List<NAFCStim>, ProceduralRandGenParameters> paramsForBlocks = new LinkedHashMap<>();

    @Override
    protected void addTrials() {
        getStims().clear();
        for (List<NAFCStim> stimBlock : stimBlocks) {
            getStims().addAll(stimBlock);
        }
    }

    public void removeBlock(int blockIndex){
        List<NAFCStim> removedBlock = stimBlocks.remove(blockIndex);
        paramsForBlocks.remove(removedBlock);
    }

    public void addBlock(Map.Entry<List<NAFCStim>, ProceduralRandGenParameters> block){
        stimBlocks.add(block.getKey());
        paramsForBlocks.put(block.getKey(), block.getValue());
    }

    public void editBlock(int blockIndex, Map.Entry<List<NAFCStim>, ProceduralRandGenParameters> block){
        stimBlocks.set(blockIndex, block.getKey());
        paramsForBlocks.put(block.getKey(), block.getValue());
    }

    public List<NAFCStim> getBlock(int blockIndex){
        return stimBlocks.get(blockIndex);
    }

    public ProceduralRandGenParameters getParamsForBlock(int blockIndex){
        List<NAFCStim> block = getBlock(blockIndex);
        return paramsForBlocks.get(block);
    }

    public String convertGeneratorNoiseMapToExperiment(String generatorPath) {
        return generatorPath.replace(getGeneratorNoiseMapPath(), getExperimentNoiseMapPath());
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
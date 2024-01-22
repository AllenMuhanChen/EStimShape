package org.xper.allen.nafc.blockgen.procedural;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

public class NAFCBlockGen extends AbstractMStickPngTrialGenerator<Stim> {

    @Dependency
    String generatorNoiseMapPath;

    @Dependency
    String experimentNoiseMapPath;

    @Dependency
    NAFCTrialParamDbUtil nafcTrialDbUtil;

    List<List<NAFCStim>> stimBlocks = new LinkedList<List<NAFCStim>>();
    Map<List<NAFCStim>, ProceduralRandGenParameters> paramsForBlocks = new LinkedHashMap<>();
    Map<List<NAFCStim>,ProceduralRandGenType> genTypesForBlocks = new LinkedHashMap<>();

    @Override
    protected void preWriteTrials() {
        int index=1;
        for(Stim stim : getStims()){
            stim.preWrite();
            System.out.println("SUCCESSFULLY WROTE STIM: " + index);
            index++;
        }
    }

    public void uploadTrialParams() {
        long tstamp = globalTimeUtil.currentTimeMicros();
        Map<ProceduralRandGenParameters, String> genTypesForParams = new LinkedHashMap<>();
        genTypesForBlocks.forEach(new BiConsumer<List<NAFCStim>, ProceduralRandGenType>() {
            @Override
            public void accept(List<NAFCStim> nafcStims, ProceduralRandGenType proceduralRandGenType) {
                genTypesForParams.put(paramsForBlocks.get(nafcStims), proceduralRandGenType.getLabel());
            }
        });
        String xml = new MixedParams(genTypesForParams).toXml();
        nafcTrialDbUtil.writeTrialParams(tstamp, xml);
    }

    public Map<ProceduralRandGenParameters, String> downloadTrialParams(){
        String xml = nafcTrialDbUtil.readLatestTrialParams();
        if (xml == null || xml.isEmpty()) {
            return null;
        }
        MixedParams mixedParams = MixedParams.fromXml(xml);
        return mixedParams.paramsForGenTypes;

    }

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

    public void addBlock(ProceduralRandGenType genType){
        Map.Entry<List<NAFCStim>, ProceduralRandGenParameters> block = genType.genBlock();
        genTypesForBlocks.put(block.getKey(), genType);
        stimBlocks.add(block.getKey());
        paramsForBlocks.put(block.getKey(), block.getValue());
    }

    public void editBlock(int blockIndex, ProceduralRandGenType genType){
//        genTypesForBlocks.put(stimBlocks.get(blockIndex), genType);
        paramsForBlocks.remove(stimBlocks.get(blockIndex));
        Map.Entry<List<NAFCStim>, ProceduralRandGenParameters> block = genType.genBlock();
        stimBlocks.set(blockIndex, block.getKey());
        paramsForBlocks.put(block.getKey(), block.getValue());
        genTypesForBlocks.put(block.getKey(), genType);
    }

    public List<NAFCStim> getBlock(int blockIndex){
        return stimBlocks.get(blockIndex);
    }

    public ProceduralRandGenParameters getParamsForBlock(int blockIndex){
        List<NAFCStim> block = getBlock(blockIndex);
        return paramsForBlocks.get(block);
    }

    public ProceduralRandGenType getTypeForBlock(int blockIndex){
        List<NAFCStim> block = getBlock(blockIndex);
        return genTypesForBlocks.get(block);
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

    public NAFCTrialParamDbUtil getNafcTrialDbUtil() {
        return nafcTrialDbUtil;
    }

    public void setNafcTrialDbUtil(NAFCTrialParamDbUtil nafcTrialDbUtil) {
        this.nafcTrialDbUtil = nafcTrialDbUtil;
    }
}
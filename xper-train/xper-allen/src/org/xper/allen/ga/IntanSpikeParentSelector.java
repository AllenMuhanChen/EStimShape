package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.TaskDoneEntry;
import org.xper.intan.read.SpikeReader;

import java.io.File;
import java.io.FileFilter;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;

public class IntanSpikeParentSelector implements ParentSelector{

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    String spikeDatDirectory;

    @Dependency
    ParentSelectorStrategy spikeRateAnalyzer;

    private List<Long> previousGenerationIds;

    public List<Long> selectParents(List<String> channels, String gaName) {

        //Read Recent Generation into list of taskIds
        GenerationTaskDoneList taskDoneList = dbUtil.readTaskDoneForGaAndGeneration(gaName, dbUtil.readTaskDoneMaxGenerationIdForGa(gaName));
        List<TaskDoneEntry> doneTasks = taskDoneList.getDoneTasks();
        previousGenerationIds = new LinkedList<>();
        for(TaskDoneEntry task:doneTasks){
            previousGenerationIds.add(task.getTaskId());
        }

        //analyze stims
        List<Double> spikeRates = new ArrayList<>();
        for (Long stimId: previousGenerationIds){
            String spikeDatPath = getSpikeDatPathFor(stimId);
            spikeRates.add(getSummedSpikeRatesFrom(channels, spikeDatPath));
        }

        return selectParentsFrom(spikeRates);
    }

    private List<Long> selectParentsFrom(List<Double> spikeRates) {
        List<Long> parents = new LinkedList<>();

        parents.addAll(spikeRateAnalyzer.analyze(Parent.createParentListFrom(previousGenerationIds, spikeRates)));
        return parents;
    }

    private Double getSummedSpikeRatesFrom(List<String> channels, String spikeDatPath) {
        SpikeReader spikeReader = new SpikeReader(spikeDatPath);
        double summedSpikeRate=0;
        for (String channel:channels){
            summedSpikeRate += spikeReader.getSpikeRate(channel);
        }
        return summedSpikeRate;
    }

    @SuppressWarnings("ConstantConditions")
    private String getSpikeDatPathFor(Long stimId) {
        File dir = new File(spikeDatDirectory);
        File[] matchingSpikeDats = dir.listFiles(new FileFilter() {
            @Override
            public boolean accept(File pathname) {
                return pathname.getName().contains(stimId + "_");
            }
        });
        if (matchingSpikeDats.length == 1){
            return matchingSpikeDats[0].getAbsolutePath() + "/spike.dat";
        } else{
            throw new IllegalArgumentException("There's either none or too many" +
                    "spike.dat files matching the stimId: " + stimId);
        }
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }


    public String getSpikeDatDirectory() {
        return spikeDatDirectory;
    }

    public void setSpikeDatDirectory(String spikeDatDirectory) {
        this.spikeDatDirectory = spikeDatDirectory;
    }

    public ParentSelectorStrategy getSpikeRateAnalyzer() {
        return spikeRateAnalyzer;
    }

    public void setSpikeRateAnalyzer(ParentSelectorStrategy spikeRateAnalyzer) {
        this.spikeRateAnalyzer = spikeRateAnalyzer;
    }


}

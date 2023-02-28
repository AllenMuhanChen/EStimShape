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

/**
 * Selects parents based on spike rate read by Intan
 */
public class StandardParentSelector implements ParentSelector{

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    IntanSpikeRateSource intanSpikeRateSource;


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
        return new LinkedList<>(spikeRateAnalyzer.analyze(Parent.createParentListFrom(previousGenerationIds, spikeRates)));
    }

    private Double getSummedSpikeRatesFrom(List<String> channels, String spikeDatPath) {
        SpikeReader spikeReader = new SpikeReader(spikeDatPath);
        double summedSpikeRate=0;
        for (String channel:channels){
            summedSpikeRate += spikeReader.getSpikeRate(channel);
        }
        return summedSpikeRate;
    }


    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public ParentSelectorStrategy getSpikeRateAnalyzer() {
        return spikeRateAnalyzer;
    }

    public void setSpikeRateAnalyzer(ParentSelectorStrategy spikeRateAnalyzer) {
        this.spikeRateAnalyzer = spikeRateAnalyzer;
    }


}

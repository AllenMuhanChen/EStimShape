package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;
import java.util.function.Consumer;

/**
 * Selects parents based on average spike rate across multiple repetitions.
 */
public class AverageSpikeRateParentSelector implements ParentSelector{

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    ParentAnalysisStrategy parentAnalysisStrategy;

    public List<Long> selectParents(String gaName) {
        Map<Long, List<Long>> taskIdsForStimIds = dbUtil.readTaskDoneIdsForStimIds(gaName, dbUtil.readTaskDoneMaxGenerationIdForGa(gaName));
        Map<Long, List<Double>> spikeRatesForStimIds = getSpikeRatesForEachStimId(taskIdsForStimIds);
        Map<Long, Double> averageSpikeRateForStimIds = calculateAverageSpikeRateForEachStimId(spikeRatesForStimIds);
        Map<Long, ParentData> parentDataForStimId = convertToParentData(averageSpikeRateForStimIds);
        return parentAnalysisStrategy.selectParents(parentDataForStimId);
    }

    private Map<Long, List<Double>> getSpikeRatesForEachStimId(Map<Long, List<Long>> taskIdsForStimId) {
        Map<Long, List<Double>> spikeRatesForStimId = new HashMap<>();
        taskIdsForStimId.forEach(new BiConsumer<Long, List<Long>>() {
            @Override
            public void accept(Long stimId, List<Long> taskIds) {

                //Read the spike rates for each taskId
                taskIds.forEach(new Consumer<Long>() {
                    @Override
                    public void accept(Long taskId) {
                        if (spikeRatesForStimId.get(stimId) == null) {
                            spikeRatesForStimId.put(stimId, new LinkedList<>());
                        }
                        spikeRatesForStimId.get(stimId).addAll(spikeRateSource.getSpikeRates(taskId));
                    }
                });
            }
        });
        return spikeRatesForStimId;
    }

    private Map<Long, Double> calculateAverageSpikeRateForEachStimId(Map<Long, List<Double>> spikeRatesForStimId) {
        Map<Long, Double> averageSpikeRateForStimId = new HashMap<>();
        spikeRatesForStimId.forEach(new BiConsumer<Long, List<Double>>() {
            @Override
            public void accept(Long stimId, List<Double> spikeRates) {
                double sum = 0;
                for (double spikeRate: spikeRates){
                    sum += spikeRate;
                }
                averageSpikeRateForStimId.put(stimId, sum/spikeRates.size());
            }
        });
        return averageSpikeRateForStimId;
    }

    private Map<Long, ParentData> convertToParentData(Map<Long, Double> averageSpikeRateForStimIds) {
        Map<Long, ParentData> parentDataForStimId = new HashMap<>();
        averageSpikeRateForStimIds.forEach(new BiConsumer<Long, Double>() {
            @Override
            public void accept(Long stimId, Double averageSpikeRate) {
                parentDataForStimId.put(stimId, new ParentData(stimId, averageSpikeRate));
            }
        });
        return parentDataForStimId;
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public ParentAnalysisStrategy getParentSelectorStrategy() {
        return parentAnalysisStrategy;
    }

    public void setParentSelectorStrategy(ParentAnalysisStrategy parentAnalysisStrategy) {
        this.parentAnalysisStrategy = parentAnalysisStrategy;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }
}
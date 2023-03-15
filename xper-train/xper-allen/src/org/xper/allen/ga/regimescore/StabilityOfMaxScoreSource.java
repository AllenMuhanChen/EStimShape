package org.xper.allen.ga.regimescore;

import org.xper.Dependency;
import org.xper.allen.ga.MaxResponseSource;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;
import java.util.stream.Collectors;

/**
 * For each generation in a lineage, calculates the max response across children
 * from the beginning of lineage up until and including that generation.
 *
 * Then, calculates the stability of the most recent N generations
 * by calculating the range of max-responses across the N generations.
 *
 * Then calculates a score between 0-1 where 0 is the least stable (highest range)
 * and 1 is when the range is less than or equal to the range threshold.
 *
 * If is the range is greater than the range threshold, the score is truncated to 1.
 */
public class StabilityOfMaxScoreSource implements LineageScoreSource{

    @Dependency
    static int N = 3;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    MaxResponseSource maxResponseSource;

    @Dependency
    ThresholdSource normalizedRangeThresholdSource;


    private Long lineageId;

    @Override
    public Double getLineageScore(Long lineageId) {
        this.lineageId = lineageId;
        //Get a Map of all genIds and their stimIds for a lineage
        LinkedHashMap<Integer, List<Long>> stimIdsForGenIds = (LinkedHashMap<Integer, List<Long>>) dbUtil.readStimIdsFromGenIdsFor(lineageId);

        //For each genId in the map, find max of all spike rates in generations up to that genId
        LinkedHashMap<Integer, Double> maxSpikeRateUpToGenIds = new LinkedHashMap<>();
        stimIdsForGenIds.forEach(new BiConsumer<Integer, List<Long>>() {
            @Override
            public void accept(Integer currentGenId, List<Long> stimIds) {
                //Find max of all spike rates up to that currentGenId
                List<Integer> genIdsUpToCurrentGenId = stimIdsForGenIds.keySet().stream().filter(key -> key <= currentGenId).collect(Collectors.toList());
                List<Long> stimIdsFromGensUpToCurrent = genIdsUpToCurrentGenId.stream().flatMap(key -> stimIdsForGenIds.get(key).stream()).collect(Collectors.toList());
                Double maxSpikeRate = calculateMaxSpikeRateFor(stimIdsFromGensUpToCurrent);
                maxSpikeRateUpToGenIds.put(currentGenId, maxSpikeRate);
            }
        });

        //Find stability of that max
        Double score = calculateStability(maxSpikeRateUpToGenIds);
        if (score > 1.0) {
            score = 1.0;
        }
        return score;
    }

    private Double calculateStability(LinkedHashMap<Integer, Double> maxSpikeRateUpToGenIds) {
        //Sort the map by genId
        Map<Integer, Double> sortedMap = maxSpikeRateUpToGenIds.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue,
                        (oldValue, newValue) -> oldValue, LinkedHashMap::new));

        //Get the last N values (aka the most recent N generations)
        List<Double> lastNValues;
        try {
            lastNValues = sortedMap.values().stream().skip(sortedMap.size() - N).collect(Collectors.toList());
        } catch (IllegalArgumentException e) {
            //If There are not enough generations, return 0.0
            return 0.0;
        }
        //Calculate the range of those values
        Double min = lastNValues.stream().min(Double::compare).get();
        Double max = lastNValues.stream().max(Double::compare).get();
        Double range = max - min;
        Double rangeThreshold = calculateRangeThreshold();
        return rangeThreshold / range;
    }

    private Double calculateRangeThreshold() {
        Double maxResponse = maxResponseSource.getMaxResponse(dbUtil.readGaNameFor(lineageId));
        Double normalizedRangeThreshold = normalizedRangeThresholdSource.getThreshold();
        return maxResponse * normalizedRangeThreshold;
    }

    private Double calculateMaxSpikeRateFor(List<Long> stimIds) {
        Map<Long, Double> averageSpikeRateForStimIds = new HashMap<Long, Double>();
        for (Long stimId : stimIds) {
            Double averageSpikeRate = spikeRateSource.getSpikeRate(stimId);
            averageSpikeRateForStimIds.put(stimId, averageSpikeRate);
        }

        // return max spike rate
        Double max = averageSpikeRateForStimIds.values().stream().max(Double::compare).get();
        return max;
    }

    private Double getAverageSpikeRate(List<Double> spikeRates) {
        Double sum = 0.0;
        for (Double spikeRate : spikeRates) {
            sum += spikeRate;
        }
        return sum / spikeRates.size();
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public static int getN() {
        return N;
    }

    public static void setN(int n) {
        N = n;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }

    public MaxResponseSource getMaxResponseSource() {
        return maxResponseSource;
    }

    public void setMaxResponseSource(MaxResponseSource maxResponseSource) {
        this.maxResponseSource = maxResponseSource;
    }

    public ThresholdSource getNormalizedRangeThresholdSource() {
        return normalizedRangeThresholdSource;
    }

    public void setNormalizedRangeThresholdSource(ThresholdSource normalizedRangeThresholdSource) {
        this.normalizedRangeThresholdSource = normalizedRangeThresholdSource;
    }
}
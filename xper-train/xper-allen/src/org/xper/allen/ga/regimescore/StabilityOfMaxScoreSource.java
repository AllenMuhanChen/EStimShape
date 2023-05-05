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
import java.util.function.Predicate;
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
    int N = 4;

    @Dependency
    String stimType;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    MaxResponseSource maxResponseSource;

    @Dependency
    ValueSource normalizedRangeValueSource;


    private Long lineageId;
    private Double maxResponse;

    @Override
    public Double getLineageScore(Long lineageId) {
        this.lineageId = lineageId;
        maxResponse = maxResponseSource.getValue(dbUtil.readGaNameFor(lineageId));
        //Get a Map of all genIds and their stimIds for a lineage
        HashMap<Integer, List<Long>> stimIdsForGenIds = (HashMap<Integer, List<Long>>) dbUtil.readStimIdsFromGenIdsFor(lineageId);

        // Filter by generations that contain a stimType stimulus
        stimIdsForGenIds = (HashMap<Integer, List<Long>>) stimIdsForGenIds.entrySet().stream().filter(
                new Predicate<Map.Entry<Integer, List<Long>>>() {
                    @Override
                    public boolean test(Map.Entry<Integer, List<Long>> entry) {
                        for (Long stimId : entry.getValue()) {
                            if (dbUtil.readStimTypeFor(stimId).equals(stimType)) {
                                return true;
                            }
                        }
                        return false;
                    }
                }
        ).collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));


        //For each genId in the map, find max of all spike rates in generations up to that genId
        LinkedHashMap<Integer, Double> maxSpikeRateUpToGenIds = new LinkedHashMap<>();
        HashMap<Integer, List<Long>> finalStimIdsForGenIds = stimIdsForGenIds;
        stimIdsForGenIds.forEach(new BiConsumer<Integer, List<Long>>() {
            @Override
            public void accept(Integer currentGenId, List<Long> stimIds) {
                //Find max of all spike rates up to that currentGenId
                List<Integer> genIdsUpToCurrentGenId = finalStimIdsForGenIds.keySet().stream().filter(
                        key -> key <= currentGenId).collect(Collectors.toList());
                List<Long> stimIdsFromGensUpToCurrent = genIdsUpToCurrentGenId.stream().flatMap(key -> finalStimIdsForGenIds.get(key).stream()).collect(Collectors.toList());
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
        LinkedHashMap<Integer, Double> sortedMap = maxSpikeRateUpToGenIds.entrySet().stream()
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
        Double normalizedRangeThreshold = normalizedRangeValueSource.getValue();
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

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public int getN() {
        return N;
    }

    public void setN(int n) {
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

    public ValueSource getNormalizedRangeThresholdSource() {
        return normalizedRangeValueSource;
    }

    public void setNormalizedRangeThresholdSource(ValueSource normalizedRangeValueSource) {
        this.normalizedRangeValueSource = normalizedRangeValueSource;
    }

    public String getStimType() {
        return stimType;
    }

    public void setStimType(String stimType) {
        this.stimType = stimType;
    }
}
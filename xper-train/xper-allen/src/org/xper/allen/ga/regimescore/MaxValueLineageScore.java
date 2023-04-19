package org.xper.allen.ga.regimescore;

import org.xper.Dependency;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.xper.allen.newga.blockgen.NewGABlockGenerator.*;

/**
 * Calculates the max response so far in a lineage and returns a number between 0-1
 * where 1 is when the max response is greater or equal to the threshold, and 0 is when the max response
 * is zero.
 */
public class MaxValueLineageScore implements LineageScoreSource {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    ValueSource maxValueSource;

    @Override
    public Double getLineageScore(Long lineageId) {
        // get all stim_ids from lineageId of type RAND
        String stimType = stimTypeForRegime.get(Regime.ZERO);
        List<Long> stimIds = dbUtil.readStimIdsFromLineageAndType(lineageId, stimType);

        // find spike rates of all stim_ids
        Double max = calculateMaxSpikeRateFor(stimIds);

        // normalize by threshold such that when max == threshold, score == 1
        Double threshold = maxValueSource.getValue();
        Double score = max / threshold;
        if (score > 1.0) {
            score = 1.0;
        }
        return score;
    }

    private Double calculateMaxSpikeRateFor(List<Long> stimIds) {
        Map<Long, Double> averageSpikeRateForStimIds = new HashMap<Long, Double>();
        for (Long stimId : stimIds) {
            Double averageSpikeRate = spikeRateSource.getSpikeRate(stimId);
            averageSpikeRateForStimIds.put(stimId, averageSpikeRate);
        }

        // return max spike rate
        Double max = averageSpikeRateForStimIds.values().stream().max(Double::compare).get();
        System.out.println("Max spike rate: " + max);
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

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }

    public ValueSource getMaxThresholdSource() {
        return maxValueSource;
    }

    public void setMaxThresholdSource(ValueSource maxValueSource) {
        this.maxValueSource = maxValueSource;
    }
}
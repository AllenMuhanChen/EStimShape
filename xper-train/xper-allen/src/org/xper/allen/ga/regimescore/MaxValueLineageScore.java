package org.xper.allen.ga.regimescore;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.Dependency;
import org.xper.allen.ga.MaxResponseSource;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MaxValueLineageScore implements LineageScoreSource {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    ThresholdSource thresholdSource;

    @Override
    public Double getLineageScore(Long lineageId) {
        // get all stim_ids from lineageId of type RAND
        List<Long> stimIds = dbUtil.readStimIdsFromLineageAndType(lineageId, "RAND");

        // find spike rates of all stim_ids
        Map<Long, Double> averageSpikeRateForStimIds = new HashMap<Long, Double>();
        for (Long stimId : stimIds) {
            List<Double> spikeRates = spikeRateSource.getSpikeRates(stimId);
            Double averageSpikeRate = getAverageSpikeRate(spikeRates);
            averageSpikeRateForStimIds.put(stimId, averageSpikeRate);
        }

        // return max spike rate
        Double max = averageSpikeRateForStimIds.values().stream().max(Double::compare).get();

        // normalize by threshold such that when max == threshold, score == 1
        Double threshold = thresholdSource.getThreshold();
        Double score = max / threshold;
        if (score > 1.0) {
            score = 1.0;
        }
        return score;
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

    public ThresholdSource getThresholdSource() {
        return thresholdSource;
    }

    public void setThresholdSource(ThresholdSource thresholdSource) {
        this.thresholdSource = thresholdSource;
    }
}
package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.ga.regimescore.LineageValueSource;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.allen.util.TikTok;

import java.util.List;

public class MaxResponseSource implements LineageValueSource {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Double minimumMaxResponse; //if the true max response is below this, set this as the max response

    @Dependency
    SpikeRateSource spikeRateSource;

    private Long lastGenIdMaxReadFrom = -1L;
    private Double maxResponse;


    @Override
    public double getValue(long lineageId) {
        return getValue(dbUtil.readGaNameFor(lineageId));
    }

    public double getValue(String gaName) {
        long mostRecentGenId = dbUtil.readTaskDoneMaxGenerationIdForGa(gaName);
        if (mostRecentGenId > lastGenIdMaxReadFrom) {
            maxResponse = readNewMaxResponse(gaName);
            lastGenIdMaxReadFrom = mostRecentGenId;
        }
        return maxResponse;
    }

    private Double readNewMaxResponse(String gaName) {
        List<Long> allStimIds = dbUtil.readAllDoneStimIdsForGa(gaName);

        TikTok calculatingMaxResponseTimer = new TikTok("Calculating max response");
        Double maxResponse = minimumMaxResponse;
        for (Long stimId : allStimIds) {
            Double averageSpikeRate = spikeRateSource.getSpikeRate(stimId);

            if (averageSpikeRate > maxResponse) {
                maxResponse = averageSpikeRate;

            }
        }
        calculatingMaxResponseTimer.stop();
        return maxResponse;
    }

    private Double calculateAverageSpikeRate(List<Double> spikeRates) {
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

    public Double getMinimumMaxResponse() {
        return minimumMaxResponse;
    }

    public void setMinimumMaxResponse(Double minimumMaxResponse) {
        this.minimumMaxResponse = minimumMaxResponse;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }


}
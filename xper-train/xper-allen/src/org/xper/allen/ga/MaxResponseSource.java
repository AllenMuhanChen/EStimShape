package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.List;

public class MaxResponseSource {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Double minimumMaxResponse; //if the true max response is below this, set this as the max response

    @Dependency
    SpikeRateSource spikeRateSource;

    public double getMaxResponse(String gaName) {
        List<Long> allStimIds = dbUtil.readAllDoneStimIdsForGa(gaName);

        Double maxResponse = minimumMaxResponse;
        for (Long stimId : allStimIds) {
            Double averageSpikeRate = spikeRateSource.getSpikeRate(stimId);

            if (averageSpikeRate > maxResponse) {
                maxResponse = averageSpikeRate;

            }
        }
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
package org.xper.allen.ga.regimescore;

import org.xper.Dependency;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class LineageMaxResponseSource implements LineageValueSource {

    MultiGaDbUtil dbUtil;

    @Dependency
    Double minimumMaxResponse; //if the true max response is below this, set this as the max response

    @Dependency
    SpikeRateSource spikeRateSource;

    private Long lastGenIdMaxReadFrom = -1L;
//    private Double maxResponse;
    private Map<Long, Double> maxResponseForLineageId = new HashMap<Long, Double>();
    private String gaName;

    public double getValue(long lineageId) {
        gaName = dbUtil.readGaNameFor(lineageId);
        long mostRecentGenId = dbUtil.readTaskDoneMaxGenerationIdForGa(gaName);
        if (mostRecentGenId > lastGenIdMaxReadFrom) {
            updateMaxResponses();
            lastGenIdMaxReadFrom = mostRecentGenId;
        }
        return maxResponseForLineageId.get(lineageId);
    }

    private void updateMaxResponses() {
        List<Long> lineageIds = dbUtil.readAllLineageIds(gaName);
        for (Long lineageId : lineageIds) {
            updateMaxResponseFor(lineageId);
        }
    }

    private void updateMaxResponseFor(Long lineageId) {
        List<Long> stimIds = dbUtil.readDoneStimIdsFromLineage(gaName, lineageId);

        Double maxResponse = minimumMaxResponse;
        for (Long stimId : stimIds) {
            Double averageSpikeRate = spikeRateSource.getSpikeRate(stimId);

            if (averageSpikeRate > maxResponse) {
                maxResponse = averageSpikeRate;

            }
        }

        maxResponseForLineageId.put(lineageId, maxResponse);
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
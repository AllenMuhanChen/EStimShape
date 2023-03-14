package org.xper.allen.ga.regimescore;

import org.xper.Dependency;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.LinkedList;
import java.util.List;

public class ParentChildThresholdScoreSource implements LineageScoreSource{
    @Dependency
    String stimType;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    ThresholdSource numPairThresholdSource;

    @Dependency
    ThresholdSource parentResponseThresholdSource;

    @Dependency
    ThresholdSource childResponseThresholdSource;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Override
    public Double getLineageScore(Long lineageId) {
        // Find all StimIds from this lineage and have stimType
        List<Long> stimIdsWithStimType = dbUtil.readStimIdsFromLineageAndType(lineageId, stimType);


        // Filter by stim whose parents response meets parentResponseThreshold
        // AND whose own response meets childResponseThreshold
        List<Long> passedFilter = new LinkedList<>();
        for (Long stimId : stimIdsWithStimType) {
            Double childSpikeRate = spikeRateSource.getSpikeRate(stimId);
            boolean passedChildThreshold = childSpikeRate >= childResponseThresholdSource.getThreshold();

            if (passedChildThreshold) {
                // Get parent response
                Long parentId = dbUtil.readParentFor(stimId);
                // If parent response meets threshold, add to filteredStimIds
                Double parentResponse = spikeRateSource.getSpikeRate(parentId);
                boolean passedParentThreshold = parentResponse >= parentResponseThresholdSource.getThreshold();

                if (passedParentThreshold) {
                    passedFilter.add(stimId);
                }
            }
        }

        // Calculate score as num that pass filter / numPairThreshold
        Integer numPassed = passedFilter.size();
        double score = numPassed / numPairThresholdSource.getThreshold();
        if (score > 1.0) {
            score = 1.0;
        }
        return score;
    }

    public String getStimType() {
        return stimType;
    }

    public void setStimType(String stimType) {
        this.stimType = stimType;
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public ThresholdSource getNumPairThresholdSource() {
        return numPairThresholdSource;
    }

    public void setNumPairThresholdSource(ThresholdSource numPairThresholdSource) {
        this.numPairThresholdSource = numPairThresholdSource;
    }

    public ThresholdSource getParentResponseThresholdSource() {
        return parentResponseThresholdSource;
    }

    public void setParentResponseThresholdSource(ThresholdSource parentResponseThresholdSource) {
        this.parentResponseThresholdSource = parentResponseThresholdSource;
    }

    public ThresholdSource getChildResponseThresholdSource() {
        return childResponseThresholdSource;
    }

    public void setChildResponseThresholdSource(ThresholdSource childResponseThresholdSource) {
        this.childResponseThresholdSource = childResponseThresholdSource;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }
}
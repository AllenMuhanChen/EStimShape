package org.xper.allen.ga.regimescore;

import org.xper.Dependency;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.LinkedList;
import java.util.List;

/**
 * Looks for Parent-Child pairs that meet the following criteria:
 * 1. The child's stimulus type is stimType
 * 1. Parent's response is greater than parentResponseThreshold
 * 2. Child's response is greater than childResponseThreshold
 *
 * Returns a score between 0-1 depending on the number of pairs that meet the criteria.
 * The score is the number of pairs that meet the criteria divided by a threshold of the number of pairs.
 *
 */
public class ParentChildThresholdScoreSource implements LineageScoreSource{
    @Dependency
    String stimType;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    ValueSource numPairValueSource;

    @Dependency
    LineageValueSource parentResponseThresholdSource;

    @Dependency
    LineageValueSource childResponseThresholdSource;

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
            boolean passedChildThreshold = childSpikeRate >= childResponseThresholdSource.getValue(lineageId);

            if (passedChildThreshold) {
                // Get parent response
                Long parentId = dbUtil.readParentFor(stimId);
                // If parent response meets threshold, add to filteredStimIds
                Double parentResponse = spikeRateSource.getSpikeRate(parentId);
                boolean passedParentThreshold = parentResponse >= parentResponseThresholdSource.getValue(lineageId);

                if (passedParentThreshold) {
                    passedFilter.add(stimId);
                }
            }
        }

        // Calculate score as num that pass filter / numPairThreshold
        Integer numPassed = passedFilter.size();
        double score = numPassed / numPairValueSource.getValue();
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

    public ValueSource getNumPairThresholdSource() {
        return numPairValueSource;
    }

    public void setNumPairThresholdSource(ValueSource numPairValueSource) {
        this.numPairValueSource = numPairValueSource;
    }

    public LineageValueSource getParentResponseThresholdSource() {
        return parentResponseThresholdSource;
    }

    public void setParentResponseThresholdSource(LineageValueSource parentResponseThresholdSource) {
        this.parentResponseThresholdSource = parentResponseThresholdSource;
    }

    public LineageValueSource getChildResponseThresholdSource() {
        return childResponseThresholdSource;
    }

    public void setChildResponseThresholdSource(LineageValueSource childResponseThresholdSource) {
        this.childResponseThresholdSource = childResponseThresholdSource;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }
}
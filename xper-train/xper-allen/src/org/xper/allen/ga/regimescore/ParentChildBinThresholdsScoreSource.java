package org.xper.allen.ga.regimescore;

import org.xper.Dependency;
import org.xper.allen.ga.MaxResponseSource;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

public class ParentChildBinThresholdsScoreSource implements LineageScoreSource{

    @Dependency
    String stimType;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    ThresholdSource parentResponseThresholdSource;

    @Dependency
    Map<NormalizedResponseBin, ThresholdSource> numPairThresholdSourcesForBins;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    MaxResponseSource maxResponseSource;

    private Long lineageId;
    private Double maxResponse;

    @Override
    public Double getLineageScore(Long lineageId) {
        this.lineageId = lineageId;
        maxResponse = maxResponseSource.getMaxResponse(dbUtil.readGaNameFor(lineageId));
        // Find all StimIds from this lineage and have stimType
        List<Long> stimIdsWithStimType = dbUtil.readStimIdsFromLineageAndType(lineageId, stimType);

        List<Long> passedFilter = filterByParentResponseThreshold(stimIdsWithStimType);

        LinkedHashMap<NormalizedResponseBin, List<Long>> childrenInsideBinForBins =
                assignChildrenToBins(passedFilter);

        LinkedHashMap<NormalizedResponseBin, Double> scoresForBins =
                calculateScoresForBins(childrenInsideBinForBins);

        // Calculate score such that 1 is that all bins have reached the threshold.
        double score = averageBinScores(scoresForBins);

        if (score > 1) {
            score = 1.0;
        }

        if (score != score) {
            score = 0.0;
        }
        return score;
    }

    private Double averageBinScores(LinkedHashMap<NormalizedResponseBin, Double> scoresForBins) {
        Double score = 0.0;
        for (Double binScore : scoresForBins.values()) {
            score += binScore;
        }
        score = score / scoresForBins.size();
        return score;
    }

    private LinkedHashMap<NormalizedResponseBin, Double> calculateScoresForBins(LinkedHashMap<NormalizedResponseBin, List<Long>> childrenInsideBinForBins) {
        LinkedHashMap<NormalizedResponseBin, Double> scoresForBins = new LinkedHashMap<>();
        childrenInsideBinForBins.forEach(new BiConsumer<NormalizedResponseBin, List<Long>>() {

            @Override
            public void accept(NormalizedResponseBin bin, List<Long> childrenIds) {
                Integer numChildren = childrenIds.size();
                Double pairThreshold = numPairThresholdSourcesForBins.get(bin).getThreshold();

                Double score = numChildren / pairThreshold;
                if (score > 1) {
                    score = 1.0;
                }
                scoresForBins.put(bin, score);
            }
        });
        return scoresForBins;
    }

    private LinkedHashMap<NormalizedResponseBin, List<Long>> assignChildrenToBins(List<Long> passedFilter) {
        LinkedHashMap<NormalizedResponseBin, List<Long>> childrenInsideBinForBins = new LinkedHashMap<>();
        numPairThresholdSourcesForBins.forEach(new BiConsumer<NormalizedResponseBin, ThresholdSource>() {
            @Override
            public void accept(NormalizedResponseBin bin, ThresholdSource thresholdSource) {
                for (Long stimId : passedFilter) {
                    // Normalize child response
                    Double childResponse = spikeRateSource.getSpikeRate(stimId);
                    Double normalizedResponse = childResponse / maxResponse;

                    // Compare to bin
                    if (bin.contains(normalizedResponse)) {
                        // Add to list of childreId that passed the bin's threshold.
                        if (!childrenInsideBinForBins.containsKey(bin)) {
                            childrenInsideBinForBins.put(bin, new LinkedList<>());
                        }
                        childrenInsideBinForBins.get(bin).add(stimId);
                    }
                }
            }
        });
        return childrenInsideBinForBins;
    }

    private List<Long> filterByParentResponseThreshold(List<Long> stimIdsWithStimType) {
        List<Long> passedFilter = new LinkedList<>();
        for (Long stimId : stimIdsWithStimType) {
            // Get parent response
            Long parentId = dbUtil.readParentFor(stimId);
            // If parent response meets threshold, add to filteredStimIds
            Double parentResponse = spikeRateSource.getSpikeRate(parentId);
            boolean passedParentThreshold = parentResponse >= parentResponseThresholdSource.getThreshold();

            if (passedParentThreshold) {
                passedFilter.add(stimId);
            }
        }
        return passedFilter;
    }

    public static class NormalizedResponseBin {
        public Double startPercentage;
        public Double endPercentage;

        public NormalizedResponseBin(Double startPercentage, Double endPercentage) {
            this.startPercentage = startPercentage;
            this.endPercentage = endPercentage;
        }

        public boolean contains(Double normalizedValue) {
            if (normalizedValue < 0 || normalizedValue > 1) {
                throw new IllegalArgumentException("Normalized value must be between 0 and 1");
            }
            return normalizedValue > startPercentage && normalizedValue <= endPercentage;
        }
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

    public ThresholdSource getParentResponseThresholdSource() {
        return parentResponseThresholdSource;
    }

    public void setParentResponseThresholdSource(ThresholdSource parentResponseThresholdSource) {
        this.parentResponseThresholdSource = parentResponseThresholdSource;
    }

    public Map<NormalizedResponseBin, ThresholdSource> getNumPairThresholdSourcesForBins() {
        return numPairThresholdSourcesForBins;
    }

    public void setNumPairThresholdSourcesForBins(Map<NormalizedResponseBin, ThresholdSource> numPairThresholdSourcesForBins) {
        this.numPairThresholdSourcesForBins = numPairThresholdSourcesForBins;
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
}
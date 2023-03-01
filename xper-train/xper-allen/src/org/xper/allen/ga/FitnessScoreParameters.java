package org.xper.allen.ga;

public class FitnessScoreParameters {
    private final Double averageSpikeRate;
    private final Integer treeCanopyWidth;

    public FitnessScoreParameters(Double averageSpikeRate, Integer treeCanopyWidth) {
        this.averageSpikeRate = averageSpikeRate;
        this.treeCanopyWidth = treeCanopyWidth;
    }

    public Double getAverageSpikeRate() {
        return averageSpikeRate;
    }

    public Integer getTreeCanopyWidth() {
        return treeCanopyWidth;
    }
}
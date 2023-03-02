package org.xper.allen.ga;

public class TreeFitnessScoreParameters extends FitnessScoreParameters {
    private final Integer treeCanopyWidth;

    public TreeFitnessScoreParameters(Double averageSpikeRate, Integer treeCanopyWidth) {
        super(averageSpikeRate);
        this.treeCanopyWidth = treeCanopyWidth;
    }

    public Integer getTreeCanopyWidth() {
        return treeCanopyWidth;
    }
}
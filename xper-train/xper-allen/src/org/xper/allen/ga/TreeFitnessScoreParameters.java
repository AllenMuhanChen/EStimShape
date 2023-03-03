package org.xper.allen.ga;

public class TreeFitnessScoreParameters extends FitnessScoreParameters {
    private final Integer treeCanopyWidth;

    /**
     *
     * @param normalizedSpikeRate averageSpikeRate / maxSpikeRate
     * @param treeCanopyWidth
     */
    public TreeFitnessScoreParameters(Double normalizedSpikeRate, Integer treeCanopyWidth) {
        super(normalizedSpikeRate);
        this.treeCanopyWidth = treeCanopyWidth;
    }

    public Integer getCanopyWidth() {
        return treeCanopyWidth;
    }
}
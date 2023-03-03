package org.xper.allen.ga;

public class TreeFitnessScoreParameters extends FitnessScoreParameters {
    private final Integer treeCanopyWidth;
    private String gaName;

    public TreeFitnessScoreParameters(Double averageSpikeRate, Integer treeCanopyWidth, String gaName) {
        super(averageSpikeRate);
        this.treeCanopyWidth = treeCanopyWidth;
        this.gaName = gaName;
    }

    /**
     * When gaName is not relevant, use this constructor.
     */
    public TreeFitnessScoreParameters(Double averageSpikeRate, Integer treeCanopyWidth) {
        super(averageSpikeRate);
        this.treeCanopyWidth = treeCanopyWidth;
    }

    public Integer getCanopyWidth() {
        return treeCanopyWidth;
    }

    public String getGaName() {
        return gaName;
    }

    public void setGaName(String gaName) {
        this.gaName = gaName;
    }
}
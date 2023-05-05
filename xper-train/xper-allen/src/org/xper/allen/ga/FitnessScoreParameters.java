package org.xper.allen.ga;

public class FitnessScoreParameters {
    protected final Double averageSpikeRate;

    public FitnessScoreParameters(Double averageSpikeRate) {
        this.averageSpikeRate = averageSpikeRate;
    }

    public Double getAverageSpikeRate() {
        return averageSpikeRate;
    }
}
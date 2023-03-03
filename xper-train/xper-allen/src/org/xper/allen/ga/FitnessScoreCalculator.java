package org.xper.allen.ga;

public interface FitnessScoreCalculator<T extends FitnessScoreParameters> {

    public double calculateFitnessScore(T params);
}
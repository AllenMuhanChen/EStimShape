package org.xper.allen.ga;

public abstract class FitnessScoreCalculator<T extends FitnessScoreParameters> {

    public abstract double calculateFitnessScore(T params);
}
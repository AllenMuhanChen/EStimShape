package org.xper.allen.ga.regimescore;

/**
 * Encapsulates the retrieval of a threshold value in case we want to change it dynamically
 */
public interface ThresholdSource {
    public Double getThreshold();
}
package org.xper.allen.ga.regimescore;

/**
 * Returns a number between 0-1 given a lineage Id.
 */
public interface LineageScoreSource {
    public Double getLineageScore(Long lineageId);
}
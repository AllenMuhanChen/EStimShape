package org.xper.allen.ga;

/**
 * Any method that returns a double given an id for a lineage
 */
public interface LineageScoreSource {
    public Double getLineageScore(Long lineageId);
}
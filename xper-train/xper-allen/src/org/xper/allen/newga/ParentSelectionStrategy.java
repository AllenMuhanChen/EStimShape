package org.xper.allen.newga;

import java.util.List;

public interface ParentSelectionStrategy {
    List<Long> selectParents(long lineageId, int numTrials);
}
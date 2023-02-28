package org.xper.allen.ga;

import java.util.*;

public class MaxSpikeRateParentSelectionStrategy implements ParentSelectionStrategy {


    @Override
    public List<Long> selectParents(Map<Long, ? extends ParentData> dataForParents) {
        List<Long> parents = new LinkedList<>();

        Long maxStimId = dataForParents.entrySet().stream()
                .max(Comparator.comparingDouble(e -> e.getValue().getSpikeRate()))
                .map(Map.Entry::getKey)
                .orElseThrow(NoSuchElementException::new);

        parents.add(maxStimId);

        return parents;
    }
}

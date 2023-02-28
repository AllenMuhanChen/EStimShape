package org.xper.allen.ga;

import java.util.*;
import java.util.stream.Collectors;

public class MaxSpikeRateParentSelectorStrategy implements ParentSelectorStrategy {


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

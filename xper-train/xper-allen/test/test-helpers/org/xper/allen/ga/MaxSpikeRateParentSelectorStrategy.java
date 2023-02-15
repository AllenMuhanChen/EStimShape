package org.xper.allen.ga;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.stream.Collectors;

public class MaxSpikeRateParentSelectorStrategy implements ParentSelectorStrategy {

    private List<Double> spikeRates;
    private List<Long> stimIds;

    @Override
    public List<Long> analyze(List<Parent> stims) {
        List<Long> parents = new LinkedList<>();
        spikeRates = stims.stream().map(Parent::getSpikeRate).collect(Collectors.toList());
        stims.stream().iterator().forEachRemaining(stim -> {
            stim.getId();
        });
        stimIds = stims.stream().map(Parent::getId).collect(Collectors.toList());
        Double max = Collections.max(spikeRates);
        parents.add(stimIds.get(spikeRates.indexOf(max)));

        return parents;
    }
}

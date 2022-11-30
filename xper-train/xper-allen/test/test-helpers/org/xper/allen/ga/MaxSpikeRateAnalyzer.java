package org.xper.allen.ga;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

public class MaxSpikeRateAnalyzer implements SpikeRateAnalyzer{

    @Override
    public List<Long> analyze(List<Long> stimIds, List<Double> spikeRates) {
        List<Long> parents = new LinkedList<>();
        Double max = Collections.max(spikeRates);
        parents.add(stimIds.get(spikeRates.indexOf(max)));

        return parents;
    }
}

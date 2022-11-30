package org.xper.allen.ga;

import java.util.List;

public interface SpikeRateAnalyzer {
    public List<Long> analyze(List<Long> stimIds, List<Double> spikeRates);
}

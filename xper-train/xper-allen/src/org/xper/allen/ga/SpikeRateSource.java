package org.xper.allen.ga;

import java.util.List;

public interface SpikeRateSource {
    List<Double> getSpikeRates(Long taskId);
}

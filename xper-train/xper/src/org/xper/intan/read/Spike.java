package org.xper.intan.read;

import java.util.List;

public class Spike {

    public double tstampSeconds;
    public int spikeId;
    List<Double> microVolts;

    public Spike(double tstampSeconds, int spikeId, List<Double> microVolts) {
        this.tstampSeconds = tstampSeconds;
        this.spikeId = spikeId;
        this.microVolts = microVolts;
    }
}

package org.xper.allen.monitorlinearization;

import org.xper.Dependency;

public class SinusoidGainCorrector {
    @Dependency
    private GainLookupTable gainLookupTable;

    public double getGain(double angle, String colors) {
        return gainLookupTable.getGain(angle, colors);
    }

    public void setGainLookupTable(GainLookupTable gainLookup) {
        this.gainLookupTable = gainLookup;
    }
}
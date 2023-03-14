package org.xper.allen.ga;

import org.xper.allen.ga.regimescore.Regime;

public class Child {

    private long stimId;
    private Regime regime;

    public Child(long stimId, Regime regime) {
        this.stimId = stimId;
        this.regime = regime;
    }

    public long getStimId() {
        return stimId;
    }

    public void setStimId(long stimId) {
        this.stimId = stimId;
    }

    public Regime getRegime() {
        return regime;
    }

    public void setRegime(Regime regime) {
        this.regime = regime;
    }
}
package org.xper.allen.ga;

import org.xper.allen.ga.regimescore.Regime;

public class Child {

    private long parentId;
    private Regime regime;

    public Child(long parentId, Regime regime) {
        this.parentId = parentId;
        this.regime = regime;
    }

    public long getParentId() {
        return parentId;
    }

    public void setParentId(long parentId) {
        this.parentId = parentId;
    }

    public Regime getRegime() {
        return regime;
    }

    public void setRegime(Regime regime) {
        this.regime = regime;
    }
}
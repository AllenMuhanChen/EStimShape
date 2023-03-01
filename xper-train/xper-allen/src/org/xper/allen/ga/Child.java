package org.xper.allen.ga;

public class Child {

    private long stimId;
    private MorphType morphType;

    public enum MorphType {
        GROWING, PRUNING
    }

    public Child(long stimId, MorphType morphType) {
        this.stimId = stimId;
        this.morphType = morphType;
    }

    public long getStimId() {
        return stimId;
    }

    public void setStimId(long stimId) {
        this.stimId = stimId;
    }

    public MorphType getMorphType() {
        return morphType;
    }

    public void setMorphType(MorphType morphType) {
        this.morphType = morphType;
    }
}
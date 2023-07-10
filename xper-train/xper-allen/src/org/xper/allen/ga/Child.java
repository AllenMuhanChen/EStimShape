package org.xper.allen.ga;

import org.xper.allen.ga.regimescore.MutationType;

public class Child {

    private long parentId;
    private MutationType mutationType;
    private double magnitude;

    public Child(long parentId, MutationType mutationType, double magnitude) {
        this.parentId = parentId;
        this.mutationType = mutationType;
        this.magnitude = magnitude;
    }

    public long getParentId() {
        return parentId;
    }

    public void setParentId(long parentId) {
        this.parentId = parentId;
    }

    public MutationType getMutationType() {
        return mutationType;
    }

    public void setMutationType(MutationType mutationType) {
        this.mutationType = mutationType;
    }
}
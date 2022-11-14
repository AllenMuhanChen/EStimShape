package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Trial;

public abstract class ThreeDGATrial implements Trial {
    protected final GA3DBlockGen generator;

    public ThreeDGATrial(GA3DBlockGen generator) {
        this.generator = generator;
    }
}

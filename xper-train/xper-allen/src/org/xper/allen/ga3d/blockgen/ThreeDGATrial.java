package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Trial;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.PngSpec;

public abstract class ThreeDGATrial implements Trial {
    protected final GA3DBlockGen generator;
    protected double size;
    protected Coordinates2D coords;
    protected long stimId;
    protected PngSpec stimSpec;
    protected AllenMStickData mStickData;

    public ThreeDGATrial(GA3DBlockGen generator, double size, Coordinates2D coords) {
        this.generator = generator;
        this.size = size;
        this.coords = coords;
    }

    public ThreeDGATrial(GA3DBlockGen generator) {
        this.generator = generator;
    }

    protected void writeStimSpec(long id) {
        generator.getDbUtil().writeStimSpec(id, stimSpec.toXml(), mStickData.toXml());
    }

    public RepetitionTrial createRepetition() {
        return new RepetitionTrial(generator, size, coords, stimSpec, mStickData);
    }
}

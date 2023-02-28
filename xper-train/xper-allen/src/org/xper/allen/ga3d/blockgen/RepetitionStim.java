package org.xper.allen.ga3d.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.PngSpec;

public class RepetitionStim extends ThreeDGAStim {
    long stimId;
    PngSpec spec;
    AllenMStickData mStickData;


    public RepetitionStim(GA3DBlockGenerator generator, double size, Coordinates2D coords, PngSpec spec, AllenMStickData mStickData) {
        super(generator, size, coords);
        this.spec = spec;
        this.mStickData = mStickData;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        //Assign StimSpecId
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();

        //Create StimSpec
        generator.getDbUtil().writeStimSpec(stimId, spec.toXml(), mStickData.toXml());
    }

    @Override
    public Long getStimId() {
        return stimId;
    }
}

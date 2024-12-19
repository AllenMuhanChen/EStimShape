package org.xper.allen.isoluminant;

import org.xper.allen.Stim;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.util.ThreadUtil;

public class MixedGaborStim implements Stim {
    private MixedGaborSpec mixedSpec;
    private IsoGaborTrialGenerator generator;
    IsoGaborSpec chromaticSpec;
    GaborSpec luminanceSpec;
    private long stimSpecId;


    public MixedGaborStim(IsoGaborTrialGenerator generator, IsoGaborSpec chromaticSpec, GaborSpec luminanceSpec) {
        this.generator = generator;
        this.chromaticSpec = chromaticSpec;
        this.luminanceSpec = luminanceSpec;

        this.mixedSpec = new MixedGaborSpec(chromaticSpec, luminanceSpec, "RedGreenMixed");
    }

    public void preWrite() {
        ThreadUtil.sleep(1);
        stimSpecId = generator.getGlobalTimeUtil().currentTimeMicros();
    }

    public void writeStim() {
        generator.getDbUtil().writeStimSpec(stimSpecId, mixedSpec.toXml());
    }

    public Long getStimId() {
        return stimSpecId;
    }
}
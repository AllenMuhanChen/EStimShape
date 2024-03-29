package org.xper.allen.isoluminant;

import org.xper.allen.Stim;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;
import org.xper.util.ThreadUtil;

public class IsoGaborStim implements Stim {
    private IsoGaborTrialGenerator generator;
    IsoGaborSpec spec;
    private long stimSpecId;


    public IsoGaborStim(IsoGaborTrialGenerator generator, IsoGaborSpec spec) {
        this.generator = generator;
        this.spec = spec;
    }

    @Override
    public void preWrite() {
        stimSpecId = generator.getGlobalTimeUtil().currentTimeMicros();
        ThreadUtil.sleep(1);
    }

    @Override
    public void writeStim() {
        generator.getDbUtil().writeStimSpec(stimSpecId, spec.toXml());
    }

    @Override
    public Long getStimId() {
        return stimSpecId;
    }
}
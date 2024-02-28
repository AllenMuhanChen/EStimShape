package org.xper.allen.monitorlinearization;

import org.xper.allen.Stim;
import org.xper.drawing.RGBColor;

public class MonLinStim implements Stim {
    private final MonLinTrialGenerator generator;
    RGBColor color;
    private long taskId;

    public MonLinStim(MonLinTrialGenerator generator, RGBColor color) {
        this.color = color;
        this.generator = generator;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        taskId = generator.getGlobalTimeUtil().currentTimeMicros();
        MonLinSpec spec = new MonLinSpec();
        spec.color = color;
        generator.getDbUtil().writeStimSpec(taskId, spec.toXml());
    }

    @Override
    public Long getTaskId() {
        return taskId;
    }
}
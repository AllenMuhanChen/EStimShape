package org.xper.allen.monitorlinearization;

import org.xper.allen.Stim;
import org.xper.drawing.RGBColor;

public class MonLinStim implements Stim {
    private final MonLinTrialGenerator generator;
    RGBColor color;
    double angle;
    double gain;
    private long taskId;

    /**
     * For MonLin only
     * @param generator
     * @param color
     */
    public MonLinStim(MonLinTrialGenerator generator, RGBColor color) {
        this.color = color;
        this.generator = generator;
        this.angle = 0;
        this.gain = 1;
    }

    /**
     * For isoluminance calibration
     * @param generator
     * @param color
     * @param angle
     */
    public MonLinStim(MonLinTrialGenerator generator, RGBColor color, double angle, double gain) {
        this.color = color;
        this.generator = generator;
        this.angle = angle;
        this.gain = gain;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        taskId = generator.getGlobalTimeUtil().currentTimeMicros();
        MonLinSpec spec = new MonLinSpec();
        spec.color = color;
        spec.angle = angle;
        spec.gain = gain;
        generator.getDbUtil().writeStimSpec(taskId, spec.toXml());
    }

    @Override
    public Long getStimId() {
        return taskId;
    }
}
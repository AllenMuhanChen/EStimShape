package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;

/**
 * @author Allen Chen
 *
 * To make your own NamingStrategy, make a new class that extends this one
 * and implement rename(). You can use context to get any information you need
 * about the trial/experiment and IntanController to get the pre-set savePath and
 * baseFilename.
 */
public abstract class IntanFileNamingStrategy {
    @Dependency
    IntanRecordingController intanRecordingController;

    public abstract void rename(TrialContext context);

    public IntanRecordingController getIntanController() {
        return intanRecordingController;
    }

    public void setIntanController(IntanRecordingController intanRecordingController) {
        this.intanRecordingController = intanRecordingController;
    }
}
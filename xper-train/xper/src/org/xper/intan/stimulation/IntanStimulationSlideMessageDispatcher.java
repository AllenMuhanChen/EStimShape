package org.xper.intan.stimulation;

import org.xper.Dependency;
import org.xper.intan.IntanRecordingSlideMessageDispatcher;

public class IntanStimulationSlideMessageDispatcher extends IntanRecordingSlideMessageDispatcher {
    @Dependency
    IntanStimulationController intanController;

    @Override
    public IntanStimulationController getIntanController() {
        return intanController;
    }

    public void setIntanController(IntanStimulationController intanController) {
        this.intanController = intanController;
    }
}
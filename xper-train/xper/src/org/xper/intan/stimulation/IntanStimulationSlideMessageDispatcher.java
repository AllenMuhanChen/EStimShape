package org.xper.intan.stimulation;

import org.xper.Dependency;
import org.xper.intan.IntanRecordingSlideMessageDispatcher;

public class IntanStimulationSlideMessageDispatcher extends IntanRecordingSlideMessageDispatcher {
    @Dependency
    ManualTriggerIntanStimulationController intanController;

    @Override
    public ManualTriggerIntanStimulationController getIntanController() {
        return intanController;
    }

    public void setIntanController(ManualTriggerIntanStimulationController intanController) {
        this.intanController = intanController;
    }
}
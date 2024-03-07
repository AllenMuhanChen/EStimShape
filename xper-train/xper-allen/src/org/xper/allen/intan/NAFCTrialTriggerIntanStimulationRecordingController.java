package org.xper.allen.intan;

import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;
import org.xper.intan.stimulation.EStimParameters;

import java.util.Objects;

/**
 * Handles Recording and Stimulation for NAFC experiments.
 * This Controller is intended for the user to specify the EStim parameters on the Intan GUI manually,
 * using f1 key as the trigger for the stimulation.
 *
 *
 */
public class NAFCTrialTriggerIntanStimulationRecordingController extends NAFCTrialIntanStimulationRecordingController {

    @Override
    public void prepareEStim(long timestamp, TrialContext context) {
        if (connected & eStimEnabled) {
            NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
            String eStimSpec = task.geteStimSpec();
            validEStimParameters = Objects.equals(eStimSpec, "EStimEnabled");
        }
    }
}
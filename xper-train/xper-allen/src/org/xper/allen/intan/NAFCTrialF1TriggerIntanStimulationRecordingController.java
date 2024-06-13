package org.xper.allen.intan;

import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;

import java.util.Objects;

/**
 * Handles Recording and Stimulation for NAFC experiments.
 * This Controller is intended for the user to specify the EStim parameters on the Intan GUI manually,
 * using f1 key as the trigger for the stimulation.
 *
 *
 */
public class NAFCTrialF1TriggerIntanStimulationRecordingController extends NAFCTrialIntanStimulationRecordingController {

    @Override
    public void prepareEStim(long timestamp, TrialContext context) {
        System.out.println("PrepareEStim");
        System.out.println("Connected: " + connected);
        System.out.println("EStimEnabled: " + eStimEnabled);
        if (connected & eStimEnabled) {
            System.out.println("Connected and Enabled");
            NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
            System.out.println("Task EStimSpec: " + task.geteStimSpec());
            System.out.println("Task StimId: " + task.getStimId());
            String eStimSpec = task.geteStimSpec();
            validEStimParameters = Objects.equals(eStimSpec, "EStimEnabled");
            if (validEStimParameters){
                System.out.println("EStim Is Enabled");
            }
        }
    }
}
package org.xper.allen.intan;

import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;
import org.xper.intan.stimulation.EStimParameters;

/**
 * This is used to use EStimParameters xml strings to write stimulation parameters to the board
 * and to trigger the estim with marker channels via digital-in
 */
public class NAFCProgrammaticDigitalTriggerIntanStimulationRecordingController extends NAFCDigitalTriggerIntanStimulationRecordingController{
    @Override
    public void trialInit(long timestamp, TrialContext context) {
        if (recordingEnabled && !connected) {
            tryConnection();
            if (toRecord()) {
                fileNamingStrategy.rename(experimentId);
                getIntan().record();
            }
        }
    }

    @Override
    public void prepareEStim(long timestamp, TrialContext context) {
        validEStimParameters = false;
        if (connected & eStimEnabled) {
            NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
            String eStimSpec = task.geteStimSpec();
            try {
                EStimParameters eStimParameters = EStimParameters.fromXml(eStimSpec);
                getIntan().setupDigitalStimulationFor(eStimParameters);
                validEStimParameters = true;
            } catch (Exception e) {
                validEStimParameters = false;
                System.err.println("ERROR!!! Could not parse EStimSpec! EStim disabled this trial");
                e.printStackTrace();
            }
        }
    }
}

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

            System.out.println("Attempting to run impedance check in trialInit of NAFCProgrammaticDigitalTriggerIntanStimulationRecordingController");
            fileNamingStrategy.rename(experimentId);
            getIntan().testImpedance();
        }
        if (toRecord()) {
            fileNamingStrategy.rename(experimentId);
            uploadStimParameters(context);
            getIntan().record();
        }
    }

    private void uploadStimParameters(TrialContext context) {
        validEStimParameters = false;
        if (connected & eStimEnabled) {
            String eStimSpec = getEStimSpec(context);
            System.out.println("eStimSpec: " + eStimSpec);
            try {
                EStimParameters eStimParameters;
                if (eStimSpec.equals("No EStim")) {
                    eStimParameters = new EStimParameters();
                } else {
                    eStimParameters = EStimParameters.fromXml(eStimSpec);
                }
                getIntan().setupDigitalStimulationForBatched(eStimParameters);
                validEStimParameters = true;
            } catch (Exception e) {
                validEStimParameters = false;
                System.err.println("ERROR!!! Could not parse EStimSpec! EStim disabled this trial");
                e.printStackTrace();
            }
        }
    }

    @Override
    public void prepareEStim(long timestamp, TrialContext context) {
        //do nothing, since we are just going to prepare EStim during trial Init. If we don't do this,
        // we run into issues trying to upload stim parameters during fixation / while we are already recording

    }

    protected String getEStimSpec(TrialContext context) {
        NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
        String eStimSpec = task.geteStimSpec();
        return eStimSpec;
    }
}

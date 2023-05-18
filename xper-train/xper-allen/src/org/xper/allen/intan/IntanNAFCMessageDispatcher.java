package org.xper.allen.intan;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;
import org.xper.intan.IntanRecordingSlideMessageDispatcher;
import org.xper.intan.stimulation.*;

/**
 * Handles Recording and Stimulation for NAFC experiments.
 *
 * We want separate events for preparing estim and triggering it as we want more control over
 * the timing of these things rather than just relying on slide, trial or experiment events.
 *
 */
public class IntanNAFCMessageDispatcher extends IntanRecordingSlideMessageDispatcher implements EStimEventListener
{
	@Dependency
	ManualTriggerIntanStimulationController manualTriggerIntanStimulationController;


	@Override
	public void prepareEStim(long timestamp, TrialContext context) {
		if (connected) {
			NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
			String eStimSpec = task.geteStimSpec();
			try {
				EStimParameters eStimParameters = EStimParameters.fromXml(eStimSpec);
				manualTriggerIntanStimulationController.setupStimulationFor(eStimParameters);

			} catch (Exception e) {
				e.printStackTrace();
				System.err.println("Could not parse eStimSpec");
			}
		}
	}

	@Override
	public void eStimOn(long timestamp, TrialContext context) {
		manualTriggerIntanStimulationController.trigger();
	}

}
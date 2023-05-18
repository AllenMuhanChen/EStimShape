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
	ManualTriggerIntanStimulationController intanStimulationController;

	private boolean validEStimParameters = false;

	@Override
	public void prepareEStim(long timestamp, TrialContext context) {
		validEStimParameters = false;
		if (connected) {
			NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
			String eStimSpec = task.geteStimSpec();
			try {
				EStimParameters eStimParameters = EStimParameters.fromXml(eStimSpec);
				intanStimulationController.setupStimulationFor(eStimParameters);
				validEStimParameters = true;
			} catch (Exception e) {
				validEStimParameters = false;
				System.err.println("Could not parse eStimSpec! EStim disabled this trial");
				e.printStackTrace();
			}
		}
	}

	@Override
	public void eStimOn(long timestamp, TrialContext context) {
		if (connected) {
			if (validEStimParameters) {
				intanStimulationController.trigger();
			}
		}
	}

}
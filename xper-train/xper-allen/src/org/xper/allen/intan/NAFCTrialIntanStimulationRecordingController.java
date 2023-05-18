package org.xper.allen.intan;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;
import org.xper.intan.IntanRecordingController;
import org.xper.intan.stimulation.*;

/**
 * Handles Recording and Stimulation for NAFC experiments.
 *
 * We want separate events for preparing estim and triggering it as we want more control over
 * the timing of these things rather than just relying on slide, trial or experiment events.
 *
 */
public class NAFCTrialIntanStimulationRecordingController extends IntanRecordingController implements EStimEventListener
{
	@Dependency
	private
	ManualTriggerIntanRHS intan;

	@Dependency
	boolean eStimEnabled;

	private boolean validEStimParameters = false;

	@Override
	public void prepareEStim(long timestamp, TrialContext context) {
		validEStimParameters = false;
		if (connected & eStimEnabled) {
			NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
			String eStimSpec = task.geteStimSpec();
			try {
				EStimParameters eStimParameters = EStimParameters.fromXml(eStimSpec);
				getIntan().setupStimulationFor(eStimParameters);
				validEStimParameters = true;
			} catch (Exception e) {
				validEStimParameters = false;
				System.err.println("ERROR!!! Could not parse EStimSpec! EStim disabled this trial");
				e.printStackTrace();
			}
		}
	}

	@Override
	public void eStimOn(long timestamp, TrialContext context) {
		if (connected & eStimEnabled) {
			if (validEStimParameters) {
				getIntan().trigger();
			}
		}
	}

	public ManualTriggerIntanRHS getIntan() {
		return intan;
	}

	public boolean iseStimEnabled() {
		return eStimEnabled;
	}

	public void seteStimEnabled(boolean eStimEnabled) {
		this.eStimEnabled = eStimEnabled;
	}

	public void setIntan(ManualTriggerIntanRHS intan) {
		this.intan = intan;
	}
}
package org.xper.allen.intan;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.intan.IntanRecordingController;
import org.xper.intan.stimulation.*;

import java.util.Arrays;

/**
 * Handles Recording and Stimulation for NAFC experiments.
 *
 * We want separate events for preparing estim and triggering it as we want more control over
 * the timing of these things rather than just relying on slide, trial or experiment events.
 *
 */
public class NAFCTrialIntanStimulationRecordingController extends IntanRecordingController implements EStimEventListener, ChoiceEventListener
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
				System.err.println("Could not parse EStimSpec. EStim will use parameters specified" +
						" in the Intan GUI.");
				e.printStackTrace();
			}
		}
	}

	@Override
	public void eStimOn(long timestamp, TrialContext context) {
		if (connected & eStimEnabled) {
			getIntan().trigger();
		}
	}

	@Override
	public void sampleOn(long timestamp, NAFCTrialContext context) {
		if (toRecord()){
			String note = Long.toString(context.getCurrentTask().getSampleSpecId());
			getIntan().writeNote(note);
		}
	}

	@Override
	public void sampleOff(long timestamp) {

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


	@Override
	public void sampleEyeInHoldFail(long timestamp) {

	}

	@Override
	public void choicesOn(long timestamp, NAFCTrialContext context) {
		if (toRecord()){
			long[] choiceSpecIds = context.getCurrentTask().getChoiceSpecId();
			String note = Arrays.toString(choiceSpecIds);
			getIntan().writeNote(note);
		}
	}

	@Override
	public void choicesOff(long timestamp) {

	}

	@Override
	public void choiceSelectionEyeFail(long timestamp) {

	}

	@Override
	public void choiceSelectionSuccess(long timestamp, int choice) {

	}

	@Override
	public void choiceSelectionNull(long timestamp) {

	}

	@Override
	public void choiceSelectionCorrect(long timestamp, int[] rewardList) {

	}

	@Override
	public void choiceSelectionIncorrect(long timestamp, int[] rewardList) {

	}

	@Override
	public void choiceSelectionDefaultCorrect(long timestamp) {

	}
}
package org.xper.allen.intan;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.intan.IntanRecordingController;
import org.xper.intan.stimulation.*;

/**
 * Handles Recording and Stimulation for NAFC experiments.
 *
 * This is supposed to handle inside of xper specification of stimulation parameters per trial.
 *
 * The stimulation is triggered by xper code via EStimEventListener.
 *
 * We want separate events for preparing estim and triggering it as we want more control over
 * the timing of these things rather than just relying on slide, trial or experiment events.
 *
 *
 */
public class NAFCIntanStimulationRecordingController extends IntanRecordingController implements EStimEventListener, ChoiceEventListener
{
	@Dependency
	ManualTriggerIntanRHS intan;

	@Dependency
	boolean eStimEnabled;

	protected boolean validEStimParameters = false;

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
				System.out.println("EStim Triggered");
			}
		}
	}

	@Override
	public void sampleOn(long timestamp, NAFCTrialContext context) {
		if (toRecord()){
			String note = Long.toString(context.getCurrentTask().getTaskId());
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
//			long[] choiceSpecIds = context.getCurrentTask().getChoiceSpecId();
//			String note = Arrays.toString(choiceSpecIds);
			getIntan().writeNote("ChoicesOn");
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
	public void choiceSelectionCorrect(long timestamp, int[] rewardList, Context context) {

	}

	@Override
	public void choiceSelectionIncorrect(long timestamp, int[] rewardList) {

	}

	@Override
	public void choiceSelectionDefaultCorrect(long timestamp) {

	}
}
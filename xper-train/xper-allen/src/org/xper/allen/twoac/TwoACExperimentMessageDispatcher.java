package org.xper.allen.twoac;

import org.xper.allen.intan.SimpleEStimEventListener;
import org.xper.allen.intan.SimpleEStimMessage;
import org.xper.allen.saccade.SaccadeExperimentTask;
import org.xper.classic.TrialExperimentMessageDispatcher;
import org.xper.classic.vo.TrialContext;

public class TwoACExperimentMessageDispatcher extends TrialExperimentMessageDispatcher implements SimpleEStimEventListener, ChoiceEventListener{

	@Override
	public void sampleOn(long timestamp, TrialContext context) {
		TwoACExperimentTask currentTask = (TwoACExperimentTask) context.getCurrentTask();
		TwoACSampleMessage sampleMsg = new TwoACSampleMessage(currentTask.getSampleSpecId());
		String msg = sampleMsg.toXml();
		enqueue(timestamp, "SampleOn", msg);
		
	}

	@Override
	public void sampleOff(long timestamp) {
		enqueue(timestamp, "SampleOff", "");
		
	}

	@Override
	public void choicesOn(long timestamp, TrialContext context) {
		TwoACExperimentTask currentTask = (TwoACExperimentTask) context.getCurrentTask();
		TwoACChoiceMessage sampleMsg = new TwoACChoiceMessage(currentTask.getChoiceSpecId(), currentTask.getTargetEyeWinCoords(), currentTask.getTargetEyeWinSize(), currentTask.getRewardPolicy());
		String msg = sampleMsg.toXml();
		enqueue(timestamp, "ChoicesOn", msg);
	}

	@Override
	public void choicesOff(long timestamp) {
		enqueue(timestamp, "ChoicesOff", "");
		
	}

	@Override
	public void choiceSelectionEyeFail(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionEyeFail", "");
		
	}

	@Override
	public void choiceSelectionEyeBreak(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionEyeBreak", "");
		
	}

	@Override
	public void choiceSelectionOne(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionOne", "");
		
	}

	@Override
	public void choiceSelectionTwo(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionTwo", "");
		
	}

	@Override
	public void choiceSelectionNull(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionNull", "");
		
	}

	@Override
	public void choiceSelectionCorrect(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionCorrect", "");
		
	}

	@Override
	public void choiceSelectionIncorrect(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionIncorect", "");
		
	}

	@Override
	public void choiceSelectionDefaultCorrect(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionDefaultCorrect", "");
		
	}

	@Override
	/*
	 * the eStim target/coords/Id is always the first in the array (0th index)
	 */
	public void eStimOn(long timestamp, TrialContext context) {
		TwoACExperimentTask currentTask = (TwoACExperimentTask) context.getCurrentTask();
		
		SimpleEStimMessage simpleEStimMsg = new SimpleEStimMessage(timestamp, currentTask.getTargetEyeWinCoords()[0], currentTask.getTargetEyeWinSize()[0], currentTask.getChoiceSpecId()[0]);
		String msg = simpleEStimMsg.toXml();
		enqueue(timestamp, "EStimOn", msg);
		
	}

}

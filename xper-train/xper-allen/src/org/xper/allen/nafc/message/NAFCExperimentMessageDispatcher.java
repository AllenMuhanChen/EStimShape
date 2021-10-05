package org.xper.allen.nafc.message;

import java.util.Arrays;

import org.xper.allen.intan.SimpleEStimEventListener;
import org.xper.allen.intan.SimpleEStimMessage;
import org.xper.allen.nafc.console.NAFCTrialStatistics;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.TrialExperimentMessageDispatcher;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialStatistics;

public class NAFCExperimentMessageDispatcher extends TrialExperimentMessageDispatcher implements SimpleEStimEventListener, ChoiceEventListener{
	
	protected NAFCTrialStatistics trialStat  = new NAFCTrialStatistics();
	
	@Override
	public void experimentStart(long timestamp) {
		enqueue(timestamp, "ExperimentStart", "");

		trialStat.reset();
	}

	public void initialEyeInFail(long timestamp, TrialContext context) {
		enqueue(timestamp, "InitialEyeInFail", "");
		trialStat.setFixationEyeInFail(trialStat.getFixationEyeInFail()+1);
	}

	
	@Override
	public void fixationSucceed(long timestamp, TrialContext context) {
		enqueue(timestamp, "FixationSucceed", "");
		trialStat.setFixationSuccess(trialStat.getFixationSuccess()+1);
	}
	
	@Override
	public void eyeInBreak(long timestamp, TrialContext context) {
		enqueue(timestamp, "EyeInBreak", "");
		trialStat.setFixationEyeInFail(trialStat.getFixationEyeInFail()+1);
	}
	
	@Override
	public void eyeInHoldFail(long timestamp, TrialContext context) {
		enqueue(timestamp, "EyeInHoldFail", "");
		trialStat.setFixationEyeInHoldFail(trialStat.getFixationEyeInHoldFail()+1);
	}
	
	@Override
	public void sampleOn(long timestamp, TrialContext context) {
		NAFCExperimentTask currentTask = (NAFCExperimentTask) context.getCurrentTask();
		NAFCSampleMessage sampleMsg = new NAFCSampleMessage(currentTask.getSampleSpecId());
		String msg = sampleMsg.toXml();
		enqueue(timestamp, "SampleOn", msg);
		
	}

	@Override
	public void sampleOff(long timestamp) {
		enqueue(timestamp, "SampleOff", "");
		trialStat.setSampleSuccess(trialStat.getSampleSuccess()+1);
	}

	@Override
	public void sampleEyeInHoldFail(long timestamp) {
		enqueue(timestamp, "SampleEyeInHoldFail", "");
		trialStat.setSampleEyeInHoldFail(trialStat.getSampleEyeInHoldFail()+1);
	}
	
	@Override
	public void choicesOn(long timestamp, TrialContext context) {
		NAFCExperimentTask currentTask = (NAFCExperimentTask) context.getCurrentTask();
		NAFCChoiceMessage sampleMsg = new NAFCChoiceMessage(currentTask.getChoiceSpecId(), currentTask.getTargetEyeWinCoords(), currentTask.getTargetEyeWinSize(), currentTask.getRewardPolicy());
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
		trialStat.setChoiceEyeFail(trialStat.getChoiceEyeFail()+1);
	}
	
	@Override
	public void choiceSelectionSuccess(long timestamp, int choice) {
		enqueue(timestamp, "ChoiceSelectionSuccess", String.valueOf(choice));
		
	}
/*
 * 
	@Override
	public void choiceSelectionEyeBreak(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionEyeBreak", "");
		
	}
*/
	

	@Override
	public void choiceSelectionNull(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionNull", "");
		
	}

	@Override
	public void choiceSelectionCorrect(long timestamp, int[] rewardList) {
		enqueue(timestamp, "ChoiceSelectionCorrect", Arrays.toString(rewardList));
		trialStat.setChoiceCorrect(trialStat.getChoiceCorrect()+1);
	}

	@Override
	public void choiceSelectionIncorrect(long timestamp, int[] rewardList) {
		enqueue(timestamp, "ChoiceSelectionIncorect", Arrays.toString(rewardList));
		trialStat.setChoiceIncorrect(trialStat.getChoiceIncorrect()+1);
	}

	@Override
	public void choiceSelectionDefaultCorrect(long timestamp) {
		enqueue(timestamp, "ChoiceSelectionDefaultCorrect", "");
		trialStat.setChoiceRewardedIncorrect(trialStat.getChoiceRewardedIncorrect()+1);
	}

	@Override
	/*
	 * the eStim target/coords/Id is always the first in the array (0th index)
	 */
	public void eStimOn(long timestamp, TrialContext context) {
		NAFCExperimentTask currentTask = (NAFCExperimentTask) context.getCurrentTask();
		
		SimpleEStimMessage simpleEStimMsg = new SimpleEStimMessage(timestamp, currentTask.getTargetEyeWinCoords()[0], currentTask.getTargetEyeWinSize()[0], currentTask.getChoiceSpecId()[0]);
		String msg = simpleEStimMsg.toXml();
		enqueue(timestamp, "EStimOn", msg);
		
	}

	public void trialComplete(long timestamp, TrialContext context) {
		enqueue(timestamp, "TrialComplete", "");
		trialStat.setCompleteTrials(trialStat.getCompleteTrials() + 1);
	}

	public void trialStop(long timestamp, TrialContext context) {
		enqueue(timestamp, "TrialStop", "");
		enqueue(timestamp, "TrialStatistics",
				NAFCTrialStatistics.toXml(trialStat));
	}
}

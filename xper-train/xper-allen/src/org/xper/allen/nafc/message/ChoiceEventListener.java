package org.xper.allen.nafc.message;

import org.xper.allen.nafc.experiment.NAFCTrialContext;

public interface ChoiceEventListener {
	public void sampleOn(long timestamp, NAFCTrialContext context);
	public void sampleOff(long timestamp);
	public void sampleEyeInHoldFail(long timestamp);
	public void choicesOn(long timestamp, NAFCTrialContext context);
	public void choicesOff(long timestamp);
	public void choiceSelectionEyeFail(long timestamp);
	public void choiceSelectionSuccess(long timestamp, int choice);
	//public void choiceSelectionEyeBreak(long timestamp);
	public void choiceSelectionNull(long timestamp);
	public void choiceSelectionCorrect(long timestamp, int[] rewardList);
	public void choiceSelectionIncorrect(long timestamp, int[] rewardList);
	public void choiceSelectionDefaultCorrect(long timestamp);
}
package org.xper.allen.nafc.message;

import org.xper.classic.vo.TrialContext;

public interface ChoiceEventListener {
	public void sampleOn(long timestamp, TrialContext context);
	public void sampleOff(long timestamp);
	public void choicesOn(long timestamp, TrialContext context);
	public void choicesOff(long timestamp);
	public void choiceSelectionEyeFail(long timestamp);
	public void choiceSelectionSuccess(long timestamp, int choice);
	//public void choiceSelectionEyeBreak(long timestamp);
	public void choiceSelectionNull(long timestamp);
	public void choiceSelectionCorrect(long timestamp, int[] rewardList);
	public void choiceSelectionIncorrect(long timestamp, int[] rewardList);
	public void choiceSelectionDefaultCorrect(long timestamp);
}

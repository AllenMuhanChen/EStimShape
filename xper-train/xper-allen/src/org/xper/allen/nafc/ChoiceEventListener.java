package org.xper.allen.nafc;

import org.xper.classic.vo.TrialContext;

public interface ChoiceEventListener {
	public void sampleOn(long timestamp, TrialContext context);
	public void sampleOff(long timestamp);
	public void choicesOn(long timestamp, TrialContext context);
	public void choicesOff(long timestamp);
	public void choiceSelectionEyeFail(long timestamp);
	public void choiceSelectionEyeBreak(long timestamp);
	public void choiceSelectionOne(long timestamp);
	public void choiceSelectionTwo(long timestamp);
	public void choiceSelectionNull(long timestamp);
	public void choiceSelectionCorrect(long timestamp);
	public void choiceSelectionIncorrect(long timestamp);
	public void choiceSelectionDefaultCorrect(long timestamp);
}

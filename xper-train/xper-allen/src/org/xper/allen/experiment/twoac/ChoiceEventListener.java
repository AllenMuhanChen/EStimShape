package org.xper.allen.experiment.twoac;

public interface ChoiceEventListener {
	public void targetSelectionCorrect(long timestamp);
	public void targetSelectionIncorrect(long timestamp);
	public void targetSelectionNull(long timestamp);
	public void targetSelectionDefaultCorrect(long timestamp);
}

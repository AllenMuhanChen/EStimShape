/**
 * 
 */
package org.xper.eye;

import org.xper.classic.vo.TrialResult;

public class TargetSelectorResult {
	
	TrialResult selectionStatusResult;
	long targetInitialSelectionLocalTime = -1;
	
	int selection = -1;

	public TrialResult getSelectionStatusResult() {
		return selectionStatusResult;
	}

	public void setSelectionStatusResult(TrialResult selectionStatusResult) {
		this.selectionStatusResult = selectionStatusResult;
	}

	public int getSelection() {
		return selection;
	}

	public void setSelection(int selection) {
		this.selection = selection;
	}

	public long getTargetInitialSelectionLocalTime() {
		return targetInitialSelectionLocalTime;
	}

	public void setTargetInitialSelectionLocalTime(
			long targetInitialSelectionLocalTime) {
		this.targetInitialSelectionLocalTime = targetInitialSelectionLocalTime;
	}
}
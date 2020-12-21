/**
 * 
 */
package org.xper.allen.eye;

import org.xper.allen.vo.TwoACTrialResult;

public class TwoACTargetSelectorResult {
	
	TwoACTrialResult selectionStatusResult;
	long targetInitialSelectionLocalTime = -1;
	
	int selection = -1;

	public TwoACTrialResult getSelectionStatusResult() {
		return selectionStatusResult;
	}

	public void setSelectionStatusResult(TwoACTrialResult selectionStatusResult) {
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
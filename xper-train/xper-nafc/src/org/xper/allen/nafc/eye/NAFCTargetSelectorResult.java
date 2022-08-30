/**
 * 
 */
package org.xper.allen.nafc.eye;

import org.xper.allen.nafc.vo.NAFCTrialResult;

public class NAFCTargetSelectorResult {
	
	NAFCTrialResult selectionStatusResult;
	long targetInitialSelectionLocalTime = -1;
	
	int selection = -1;

	public NAFCTrialResult getSelectionStatusResult() {
		return selectionStatusResult;
	}

	public void setSelectionStatusResult(NAFCTrialResult selectionStatusResult) {
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
package org.xper.allen.nafc.experiment;

import org.xper.allen.nafc.eye.NAFCTargetSelectorResult;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;

public class NAFCTrialContext extends TrialContext {
	long sampleOnTime;
	long sampleOffTime;
	long choicesOnTime;
	long choicesOffTime;
	
	//Added 04/05/2022 for helping preallocate space for random noise
	long sampleLength;
	
	//long targetOnTime;
	long targetInitialSelectionTime;
	long targetSelectionSuccessTime;
	

	Coordinates2D[] targetPos;
	double[] targetEyeWindowSize;
	long targetIndex;
	
	NAFCTargetSelectorResult selectorResult;
	boolean targetFixationSuccess;

	public NAFCExperimentTask getCurrentTask() {
		return (NAFCExperimentTask) this.currentTask;
	}

	public void setCurrentTask(NAFCExperimentTask currentTask) {
		this.currentTask = currentTask;
	}

	public Coordinates2D[] getTargetPos() {
		return targetPos;
	}

	public void setTargetPos(Coordinates2D[] targetPos) {
		this.targetPos = targetPos;
	}

	public double[] getTargetEyeWindowSize() {
		return targetEyeWindowSize;
	}

	public void setTargetEyeWindowSize(double[] targetEyeWindowSize) {
		this.targetEyeWindowSize = targetEyeWindowSize;
	}


	public long getTargetInitialSelectionTime() {
		return targetInitialSelectionTime;
	}

	public void setTargetInitialSelectionTime(long targetInitialSelectionTime) {
		this.targetInitialSelectionTime = targetInitialSelectionTime;
	}

	public long getTargetSelectionSuccessTime() {
		return targetSelectionSuccessTime;
	}

	public void setTargetSelectionSuccessTime(long targetSelectionSuccessTime) {
		this.targetSelectionSuccessTime = targetSelectionSuccessTime;
	}

	public long getSampleOnTime() {
		return sampleOnTime;
	}

	public void setSampleOnTime(long sampleOnTime) {
		this.sampleOnTime = sampleOnTime;
	}

	public long getChoicesOnTime() {
		return choicesOnTime;
	}

	public void setChoicesOnTime(long choicesOnTime) {
		this.choicesOnTime = choicesOnTime;
	}

	public long getTargetIndex() {
		return targetIndex;
	}

	public void setTargetIndex(long targetIndex) {
		this.targetIndex = targetIndex;
	}

	public boolean isTargetFixationSuccess() {
		return targetFixationSuccess;
	}

	public void setTargetFixationSuccess(boolean targetFixationSuccess) {
		this.targetFixationSuccess = targetFixationSuccess;
	}

	public long getSampleOffTime() {
		return sampleOffTime;
	}

	public void setSampleOffTime(long sampleOffTime) {
		this.sampleOffTime = sampleOffTime;
	}

	public long getChoicesOffTime() {
		return choicesOffTime;
	}

	public void setChoicesOffTime(long choicesOffTime) {
		this.choicesOffTime = choicesOffTime;
	}

	public NAFCTargetSelectorResult getSelectorResult() {
		return selectorResult;
	}

	public void setSelectorResult(NAFCTargetSelectorResult selectorResult) {
		this.selectorResult = selectorResult;
	}

	public long getSampleLength() {
		return sampleLength;
	}

	public void setSampleLength(long sampleLength) {
		this.sampleLength = sampleLength;
	}


}

package org.xper.allen.twoac;

import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;

public class TwoACTrialContext extends TrialContext {
	long sampleOnTime;
	long sampleOffTime;
	long choicesOnTime;
	long choicesOffTime;
	
	//long targetOnTime;
	long targetInitialSelectionTime;
	long targetSelectionSuccessTime;
	

	Coordinates2D[] targetPos;
	double[] targetEyeWindowSize;
	long targetIndex;
	
	boolean targetFixationSuccess;

	public TwoACExperimentTask getCurrentTask() {
		return (TwoACExperimentTask) this.currentTask;
	}

	public void setCurrentTask(TwoACExperimentTask currentTask) {
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


}

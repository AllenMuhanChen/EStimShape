package org.xper.allen.experiment.twoac;

import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;

public class TwoACTrialContext extends TrialContext {
	long targetOnTime;
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

	public long getTargetOnTime() {
		return targetOnTime;
	}

	public void setTargetOnTime(long targetOnTime) {
		this.targetOnTime = targetOnTime;
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
	
	

}

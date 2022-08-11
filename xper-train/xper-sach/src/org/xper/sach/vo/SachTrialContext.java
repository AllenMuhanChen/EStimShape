package org.xper.sach.vo;

import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;

public class SachTrialContext extends TrialContext {
	/**
	 * Target presented for Monkey to saccade to.
	 */
	long targetOnTime;
	long targetInitialSelectionTime;
	
	long targetSelectionSuccessTime;
	
	Coordinates2D targetPos = new Coordinates2D();
	double targetEyeWindowSize;
	long targetIndex;
	
	boolean targetFixationSuccess;
	
	int countObjects;
	
	long reward;
	
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
	
	public Coordinates2D getTargetPos() {
		return targetPos;
	}
	public void setTargetPos(Coordinates2D targetPos) {
		this.targetPos = targetPos;
	}
	public double getTargetEyeWindowSize() {
		return targetEyeWindowSize;
	}
	public void setTargetEyeWindowSize(double targetEyeWindowSize) {
		this.targetEyeWindowSize = targetEyeWindowSize;
	}
	public boolean isTargetFixationSuccess() {
		return targetFixationSuccess;
	}
	public void setTargetFixationSuccess(boolean targetFixationSuccess) {
		this.targetFixationSuccess = targetFixationSuccess;
	}
	public int getCountObjects() {
		return countObjects;
	}
	public void setCountObjects(int countObjects) {
		this.countObjects = countObjects;
	}
	public long getReward() {
		return reward;
	}
	public void setReward(long reward) {
		this.reward = reward;
	}
	public long getTargetIndex() {
		return targetIndex;
	}
	public void setTargetIndex(long targetIndex) {
		this.targetIndex = targetIndex;
	}
}

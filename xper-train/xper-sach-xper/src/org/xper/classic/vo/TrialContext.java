package org.xper.classic.vo;

import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;


public class TrialContext extends Context {
	int slideIndex;
	int animationFrameIndex;
	
	long trialInitTime;
	long trialStartTime;
	long fixationPointOnTime;
	long initialEyeInTime;
	long initialEyeInFailTime;
	long eyeInHoldFailTime;
	long fixationSuccessTime;
	long eyeInBreakTime;
	long trialCompleteTime;
	long trialStopTime;
	
	long currentSlideOnTime;
	long currentSlideOffTime;
	
	ExperimentTask currentTask;
	
	public int getAnimationFrameIndex() {
		return animationFrameIndex;
	}
	public void setAnimationFrameIndex(int animationFrameIndex) {
		this.animationFrameIndex = animationFrameIndex;
	}
	public long getCurrentSlideOffTime() {
		return currentSlideOffTime;
	}
	public void setCurrentSlideOffTime(long currentSlideOffTime) {
		this.currentSlideOffTime = currentSlideOffTime;
	}
	public long getCurrentSlideOnTime() {
		return currentSlideOnTime;
	}
	public void setCurrentSlideOnTime(long currentSlideOnTime) {
		this.currentSlideOnTime = currentSlideOnTime;
	}
	public long getEyeInBreakTime() {
		return eyeInBreakTime;
	}
	public void setEyeInBreakTime(long eyeInBreakTime) {
		this.eyeInBreakTime = eyeInBreakTime;
	}
	public long getEyeInHoldFailTime() {
		return eyeInHoldFailTime;
	}
	public void setEyeInHoldFailTime(long eyeInHoldFailTime) {
		this.eyeInHoldFailTime = eyeInHoldFailTime;
	}
	public long getFixationPointOnTime() {
		return fixationPointOnTime;
	}
	public void setFixationPointOnTime(long fixationPointOnTime) {
		this.fixationPointOnTime = fixationPointOnTime;
	}
	public long getFixationSuccessTime() {
		return fixationSuccessTime;
	}
	public void setFixationSuccessTime(long fixationSuccessTime) {
		this.fixationSuccessTime = fixationSuccessTime;
	}
	public long getInitialEyeInFailTime() {
		return initialEyeInFailTime;
	}
	public void setInitialEyeInFailTime(long initialEyeInFailTime) {
		this.initialEyeInFailTime = initialEyeInFailTime;
	}
	public long getInitialEyeInTime() {
		return initialEyeInTime;
	}
	public void setInitialEyeInTime(long initialEyeInTime) {
		this.initialEyeInTime = initialEyeInTime;
	}
	public int getSlideIndex() {
		return slideIndex;
	}
	public void setSlideIndex(int slideIndex) {
		this.slideIndex = slideIndex;
	}
	public long getTrialCompleteTime() {
		return trialCompleteTime;
	}
	public void setTrialCompleteTime(long trialCompleteTime) {
		this.trialCompleteTime = trialCompleteTime;
	}
	public long getTrialStartTime() {
		return trialStartTime;
	}
	public void setTrialStartTime(long trialStartTime) {
		this.trialStartTime = trialStartTime;
	}
	public long getTrialStopTime() {
		return trialStopTime;
	}
	public void setTrialStopTime(long trialStopTime) {
		this.trialStopTime = trialStopTime;
	}
	public long getTrialInitTime() {
		return trialInitTime;
	}
	public void setTrialInitTime(long trialInitTime) {
		this.trialInitTime = trialInitTime;
	}
	public ExperimentTask getCurrentTask() {
		return currentTask;
	}
	public void setCurrentTask(ExperimentTask currentTask) {
		this.currentTask = currentTask;
	}
}

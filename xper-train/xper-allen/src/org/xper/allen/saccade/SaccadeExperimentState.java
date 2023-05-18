package org.xper.allen.saccade;

import java.util.List;

import org.xper.Dependency;
import org.xper.allen.intan.EStimEventListener;
import org.xper.allen.saccade.console.TargetEventListener;
import org.xper.eye.EyeTargetSelector;
import org.xper.util.IntanUtil;

public class SaccadeExperimentState extends SaccadeTrialExperimentState{
	@Dependency
	EyeTargetSelector targetSelector;
	@Dependency
	List<? extends TargetEventListener> targetEventListeners;
	@Dependency
	List<? extends EStimEventListener> eStimEventListeners;


	int blankTargetScreenDisplayTime;

	public EyeTargetSelector getTargetSelector() {
		return targetSelector;
	}

	public void setTargetSelector(EyeTargetSelector targetSelector) {
		this.targetSelector = targetSelector;
	}


	public SaccadeExperimentTask getCurrentTask() {
		return (SaccadeExperimentTask) currentTask;
	}

	public void setCurrentTask(SaccadeExperimentTask currentTask) {
		this.currentTask = currentTask;
	}

	public int getBlankTargetScreenDisplayTime() {
		return blankTargetScreenDisplayTime;
	}

	public void setBlankTargetScreenDisplayTime(int blankTargetScreenDisplayTime) {
		this.blankTargetScreenDisplayTime = blankTargetScreenDisplayTime;
	}


	public List<? extends TargetEventListener> getTargetEventListeners() {
		return targetEventListeners;
	}

	public void setTargetEventListeners(List<? extends TargetEventListener> targetEventListeners) {
		this.targetEventListeners = targetEventListeners;
	}


	public List<? extends EStimEventListener> geteStimEventListeners() {
		return eStimEventListeners;
	}

	public void seteStimEventListeners(List<? extends EStimEventListener> eStimEventListeners) {
		this.eStimEventListeners = eStimEventListeners;
	}

}
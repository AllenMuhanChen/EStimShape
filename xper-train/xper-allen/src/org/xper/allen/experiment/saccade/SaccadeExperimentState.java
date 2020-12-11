package org.xper.allen.experiment.saccade;

import java.util.List;

import org.xper.Dependency;
import org.xper.allen.console.TargetEventListener;
import org.xper.allen.intan.SimpleEStimEventListener;
import org.xper.eye.EyeTargetSelector;
import org.xper.util.IntanUtil;

public class SaccadeExperimentState extends SaccadeTrialExperimentState{
	@Dependency
	EyeTargetSelector targetSelector;
	@Dependency
	List<? extends TargetEventListener> targetEventListeners;
	@Dependency
	List<? extends SimpleEStimEventListener> eStimEventListeners;
	@Dependency
	IntanUtil intanUtil;
	
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

	public IntanUtil getIntanUtil() {
		return intanUtil;
	}

	public void setIntanUtil(IntanUtil intanUtil) {
		this.intanUtil = intanUtil;
	}

	public List<? extends SimpleEStimEventListener> geteStimEventListeners() {
		return eStimEventListeners;
	}

	public void seteStimEventListeners(List<? extends SimpleEStimEventListener> eStimEventListeners) {
		this.eStimEventListeners = eStimEventListeners;
	}
	
}

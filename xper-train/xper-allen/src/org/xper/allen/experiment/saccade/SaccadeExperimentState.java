package org.xper.allen.experiment.saccade;

import java.util.List;

import org.xper.Dependency;
import org.xper.allen.console.TargetEventListener;

import org.xper.eye.EyeTargetSelector;

public class SaccadeExperimentState extends SaccadeTrialExperimentState{
	@Dependency
	EyeTargetSelector targetSelector;
	@Dependency
	List<? extends TargetEventListener> targetEventListeners;
	
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
	
	/**
	 * Time for Initial Target Selection is just equal to the time the stimulus is up
	 * @author allenchen
	 */
	public long getTimeAllowedForInitialTargetSelection() {
		return (long) getCurrentTask().getDuration();
	}

	public List<? extends TargetEventListener> getTargetEventListeners() {
		return targetEventListeners;
	}

	public void setTargetEventListeners(List<? extends TargetEventListener> targetEventListeners) {
		this.targetEventListeners = targetEventListeners;
	}
	
}

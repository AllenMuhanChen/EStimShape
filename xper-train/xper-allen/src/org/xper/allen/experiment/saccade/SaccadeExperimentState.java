package org.xper.allen.experiment.saccade;

import org.xper.Dependency;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.eye.EyeTargetSelector;

public class SaccadeExperimentState extends SaccadeTrialExperimentState{
	@Dependency
	EyeTargetSelector targetSelector;
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
	
}

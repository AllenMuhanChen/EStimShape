package org.xper.allen.experiment.saccade;

import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.ExperimentTask;

public class SaccadeTrialContext extends TrialContext {
	long targetOnTime;
	long targetInitialSelectionTime;
	long targetSelectionSuccessTime;
	
	Coordinates2D targetPos = new Coordinates2D();
	double targetEyeWindowSize;
	long targetIndex;
	
	boolean targetFixationSuccess;

	public SaccadeExperimentTask getCurrentTask() {
		return this.getCurrentTask();
	}

	public void setCurrentTask(SaccadeExperimentTask currentTask) {
		this.currentTask = currentTask;
	}

}

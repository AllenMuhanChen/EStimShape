package org.xper.allen.nafc.experiment;

import java.util.List;

import org.xper.Dependency;
import org.xper.allen.intan.EStimEventListener;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.eye.EyeTargetSelector;


public class NAFCExperimentState extends NAFCTrialExperimentState{
	@Dependency
	EyeTargetSelector targetSelector;
	@Dependency
	List<? extends ChoiceEventListener> choiceEventListeners;
	@Dependency
	List<? extends EStimEventListener> eStimEventListeners;
	@Dependency
	NAFCTrialDrawingController drawingController;


	int blankTargetScreenDisplayTime;

	public EyeTargetSelector getTargetSelector() {
		return targetSelector;
	}


	public void setTargetSelector(EyeTargetSelector targetSelector) {
		this.targetSelector = targetSelector;
	}


	public NAFCExperimentTask getCurrentTask() {
		return (NAFCExperimentTask) currentTask;
	}

	public NAFCTrialDrawingController getDrawingController() {
		return drawingController;
	}

	public void setDrawingController(NAFCTrialDrawingController drawingController) {
		this.drawingController = drawingController;
	}

	public void setCurrentTask(NAFCExperimentTask currentTask) {
		this.currentTask = currentTask;
	}

	public int getBlankTargetScreenDisplayTime() {
		return blankTargetScreenDisplayTime;
	}

	public void setBlankTargetScreenDisplayTime(int blankTargetScreenDisplayTime) {
		this.blankTargetScreenDisplayTime = blankTargetScreenDisplayTime;
	}

	public List<? extends EStimEventListener> geteStimEventListeners() {
		return eStimEventListeners;
	}

	public void seteStimEventListeners(List<? extends EStimEventListener> eStimEventListeners) {
		this.eStimEventListeners = eStimEventListeners;
	}

	public List<? extends ChoiceEventListener> getChoiceEventListeners() {
		return choiceEventListeners;
	}

	public void setChoiceEventListeners(List<? extends ChoiceEventListener> choiceEventListeners) {
		this.choiceEventListeners = choiceEventListeners;
	}

}
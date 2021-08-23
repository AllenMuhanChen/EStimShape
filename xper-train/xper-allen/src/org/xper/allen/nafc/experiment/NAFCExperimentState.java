package org.xper.allen.nafc;

import java.util.List;

import org.xper.Dependency;
import org.xper.allen.intan.SimpleEStimEventListener;
import org.xper.allen.saccade.console.TargetEventListener;
import org.xper.classic.TrialDrawingController;
import org.xper.eye.EyeTargetSelector;
import org.xper.util.IntanUtil;

public class NAFCExperimentState extends NAFCTrialExperimentState{
	@Dependency
	EyeTargetSelector targetSelector;
	@Dependency
	List<? extends ChoiceEventListener> choiceEventListeners;
	@Dependency
	List<? extends SimpleEStimEventListener> eStimEventListeners;
	@Dependency
	IntanUtil intanUtil;
	@Dependency
	TrialDrawingController drawingController;
	
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
	
	public TrialDrawingController getDrawingController() {
		return drawingController;
	}

	public void setDrawingController(TrialDrawingController drawingController) {
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

	public List<? extends ChoiceEventListener> getChoiceEventListeners() {
		return choiceEventListeners;
	}

	public void setChoiceEventListeners(List<? extends ChoiceEventListener> choiceEventListeners) {
		this.choiceEventListeners = choiceEventListeners;
	}
	
}

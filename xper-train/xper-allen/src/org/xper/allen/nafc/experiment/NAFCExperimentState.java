package org.xper.allen.nafc.experiment;

import java.util.List;

import org.xper.Dependency;
import org.xper.allen.intan.EStimEventListener;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.eye.EyeTargetSelector;
import org.xper.util.IntanUtil;

public class NAFCExperimentState extends NAFCTrialExperimentState{
	@Dependency
	EyeTargetSelector targetSelector;
	@Dependency
	List<? extends ChoiceEventListener> choiceEventListeners;
	@Dependency
	List<? extends EStimEventListener> eStimEventListeners;
	@Dependency
	IntanUtil intanUtil;
	@Dependency
	NAFCTrialDrawingController drawingController;
	@Dependency
	boolean repeatIncorrectTrials;
	@Dependency
	boolean showAnswer;
	@Dependency
	int answerLength;

	int blankTargetScreenDisplayTime;
	int punishmentDelayTime;

	public EyeTargetSelector getTargetSelector() {
		return targetSelector;
	}

	public boolean isRepeatIncorrectTrials() {
		return repeatIncorrectTrials;
	}

	public boolean isShowAnswer() {
		return showAnswer;
	}

	public int getAnswerLength() {
		return answerLength;
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


	public IntanUtil getIntanUtil() {
		return intanUtil;
	}

	public void setIntanUtil(IntanUtil intanUtil) {
		this.intanUtil = intanUtil;
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

	public int getPunishmentDelayTime() {
		return punishmentDelayTime;
	}

	public void setPunishmentDelayTime(int punishmentDelayTime) {
		this.punishmentDelayTime = punishmentDelayTime;
	}

	public void setRepeatIncorrectTrials(boolean repeatIncorrectTrials) {
		this.repeatIncorrectTrials = repeatIncorrectTrials;
	}

	public void setShowAnswer(boolean showAnswer) {
		this.showAnswer = showAnswer;
	}

	public void setAnswerLength(int answerLength) {
		this.answerLength = answerLength;
	}
}
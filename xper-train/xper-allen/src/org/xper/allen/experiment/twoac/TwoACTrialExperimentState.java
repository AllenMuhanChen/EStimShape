package org.xper.allen.experiment.twoac;

import java.util.List;

import org.xper.Dependency;
import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.experiment.TaskDataSource;
import org.xper.eye.EyeTargetSelector;

public class TwoACTrialExperimentState extends TrialExperimentState {
	@Dependency
	List<? extends SlideEventListener> slideEventListeners;
	/*
	@Dependency
	protected int slidePerTrial;
	@Dependency
	int slideLength;
	@Dependency
	int interSlideInterval;
	*/
	@Dependency
	int sampleLength;
	@Dependency
	int choiceLength;
	public int getSampleLength() {
		return sampleLength;
	}

	public void setSampleLength(int sampleLength) {
		this.sampleLength = sampleLength;
	}

	public int getChoiceLength() {
		return choiceLength;
	}

	public void setChoiceLength(int choiceLength) {
		this.choiceLength = choiceLength;
	}

	@Dependency
	boolean doEmptyTask = true;
	@Dependency
	boolean repeatTrialIfEyeBreak = false; //TODO; add injection
	@Dependency
	EyeTargetSelector targetSelector;
	@Dependency
	TwoACTrialContext currentContext;
	@Dependency
	TaskDataSource taskDataSource;

	
	
	/**
	 * in ms
	 */
	public static final int NO_TASK_SLEEP_INTERVAL = 10;
	
	public boolean isDoEmptyTask() {
		return doEmptyTask;
	}

	public void setDoEmptyTask(boolean doEmptyTask) {
		this.doEmptyTask = doEmptyTask;
	}
/*
	public int getInterSlideInterval() {
		return interSlideInterval;
	}

	public void setInterSlideInterval(int interSlideInterval) {
		this.interSlideInterval = interSlideInterval;
	}

	public int getSlideLength() {
		return slideLength;
	}

	public void setSlideLength(int slideLength) {
		this.slideLength = slideLength;
	}

	public int getSlidePerTrial() {
		return slidePerTrial;
	}

	public void setSlidePerTrial(int slidePerTrial) {
		this.slidePerTrial = slidePerTrial;
	}
*/
	public List<? extends SlideEventListener> getSlideEventListeners() {
		return slideEventListeners;
	}

	public void setSlideEventListeners(
			List<? extends SlideEventListener> slideEventListeners) {
		this.slideEventListeners = slideEventListeners;
	}
	
	public TwoACExperimentTask getCurrentTask() {
		return (TwoACExperimentTask) currentTask;
	}
	
	public void setCurrentTask(TwoACExperimentTask currentTask) {
		this.currentTask = currentTask;
	}

	public EyeTargetSelector getTargetSelector() {
		return targetSelector;
	}

	public void setTargetSelector(EyeTargetSelector targetController) {
		this.targetSelector = targetController;
	}
	public TrialContext getCurrentContext() {
		return currentContext;
	}

	public void setCurrentContext(TwoACTrialContext currentContext) {
		this.currentContext = currentContext;
	}

	public boolean isRepeatTrialIfEyeBreak() {
		return repeatTrialIfEyeBreak;
	}

	public void setRepeatTrialIfEyeBreak(boolean repeatTrialIfEyeBreak) {
		this.repeatTrialIfEyeBreak = repeatTrialIfEyeBreak;
	}

	public TaskDataSource getTaskDataSource() {
		return taskDataSource;
	}

	public void setTaskDataSource(TaskDataSource taskDataSource) {
		this.taskDataSource = taskDataSource;
	}

	
	

}

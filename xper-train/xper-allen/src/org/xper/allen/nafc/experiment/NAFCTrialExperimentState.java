package org.xper.allen.nafc.experiment;

import java.util.List;

import org.xper.Dependency;
import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.experiment.TaskDataSource;
import org.xper.eye.EyeTargetSelector;

public class NAFCTrialExperimentState extends TrialExperimentState {

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

	public int getSampleLength() {
		return sampleLength;
	}

	public void setSampleLength(int sampleLength) {
		this.sampleLength = sampleLength;
	}

	@Dependency
	boolean doEmptyTask = false;
	@Dependency
	boolean repeatTrialIfEyeBreak = false; //TODO; add injection
	@Dependency
	EyeTargetSelector targetSelector;
	@Dependency
	NAFCTrialContext currentContext;
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

	public NAFCExperimentTask getCurrentTask() {
		return (NAFCExperimentTask) currentTask;
	}

	public void setCurrentTask(NAFCExperimentTask currentTask) {
		this.currentTask = currentTask;
	}

	public EyeTargetSelector getTargetSelector() {
		return targetSelector;
	}

	public void setTargetSelector(EyeTargetSelector targetController) {
		this.targetSelector = targetController;
	}

	public NAFCTrialContext getCurrentContext() {
		return currentContext;
	}

	public void setCurrentContext(NAFCTrialContext currentContext) {
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
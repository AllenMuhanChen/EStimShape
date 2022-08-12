package org.xper.classic.vo;

import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

import org.xper.Dependency;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.TaskDoneCache;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadUtil;

public class TrialExperimentState {

	@Dependency
	List<? extends TrialEventListener> trialEventListeners;
	@Dependency
	EyeController eyeController;
	@Dependency
	List<? extends ExperimentEventListener> experimentEventListeners;
	@Dependency
	TaskDataSource taskDataSource;
	@Dependency
	TaskDoneCache taskDoneCache;
	@Dependency
	TimeUtil globalTimeClient;
	@Dependency
	TrialDrawingController drawingController;
	/**
	 * in ms
	 */
	@Dependency
	int interTrialInterval;
	@Dependency
	int delayAfterTrialComplete;
	@Dependency
	int timeBeforeFixationPointOn;
	@Dependency
	int timeAllowedForInitialEyeIn;
	@Dependency
	int requiredEyeInHoldTime;
	@Dependency
	boolean sleepWhileWait = true;
	@Dependency
	TimeUtil localTimeUtil;
	
	AtomicBoolean pause = new AtomicBoolean(false);
	/**
	 * Current task being presented. When done, set it to null so that when
	 * trial stops, it can be tested for null to decide if we need to re-do it
	 * next time by unget it back into the task data source.
	 */
	ExperimentTask currentTask = null;
	TrialContext currentContext = null;
	boolean isAnimation;
	public static final int SLEEP_INTERVAL = 1;
	public static final int EXPERIMENT_PAUSE_SLEEP_INTERVAL = 10;

	public int getInterTrialInterval() {
		return interTrialInterval;
	}

	public void setInterTrialInterval(int interTrialInterval) {
		this.interTrialInterval = interTrialInterval;
	}

	public boolean isSleepWhileWait() {
		return sleepWhileWait;
	}

	public void setSleepWhileWait(boolean sleepWhileWait) {
		this.sleepWhileWait = sleepWhileWait;
	}

	public int getTimeBeforeFixationPointOn() {
		return timeBeforeFixationPointOn;
	}

	public void setTimeBeforeFixationPointOn(int timeBeforeFixationPointOn) {
		this.timeBeforeFixationPointOn = timeBeforeFixationPointOn;
	}

	public int getTimeAllowedForInitialEyeIn() {
		return timeAllowedForInitialEyeIn;
	}

	public void setTimeAllowedForInitialEyeIn(int timeAllowedForInitialEyeIn) {
		this.timeAllowedForInitialEyeIn = timeAllowedForInitialEyeIn;
	}

	public int getRequiredEyeInHoldTime() {
		return requiredEyeInHoldTime;
	}

	public void setRequiredEyeInHoldTime(int requiredEyeInHoldTime) {
		this.requiredEyeInHoldTime = requiredEyeInHoldTime;
	}

	public TaskDataSource getTaskSource() {
		return taskDataSource;
	}

	public void setTaskSource(TaskDataSource taskSource) {
		this.taskDataSource = taskSource;
	}

	public boolean isPause() {
		return pause.get();
	}

	public void setPause(boolean pause) {
		if (pause && this.pause.get() || !pause && !this.pause.get()) {
			return;
		}
		if (pause) {
			System.out
					.println("Pause experiment. Experiment will pause after the current trial.");
		} else {
			System.out.println("Resume experiment.");
		}
		this.pause.set(pause);
		
		if (currentContext != null) {
			while (currentContext.getTrialStopTime() < currentContext.getTrialStartTime()) {
				ThreadUtil.sleep(100);
			}
		}
	}

	public List<? extends ExperimentEventListener> getExperimentEventListeners() {
		return experimentEventListeners;
	}

	public void setExperimentEventListeners(
			List<? extends ExperimentEventListener> experimentEventListeners) {
		this.experimentEventListeners = experimentEventListeners;
	}

	public List<? extends TrialEventListener> getTrialEventListeners() {
		return trialEventListeners;
	}

	public void setTrialEventListeners(
			List<? extends TrialEventListener> trialEventListeners) {
		this.trialEventListeners = trialEventListeners;
	}

	public TaskDataSource getTaskDataSource() {
		return taskDataSource;
	}

	public void setTaskDataSource(TaskDataSource taskDataSource) {
		this.taskDataSource = taskDataSource;
	}

	public EyeController getEyeController() {
		return eyeController;
	}

	public void setEyeController(EyeController eyeController) {
		this.eyeController = eyeController;
	}

	public TaskDoneCache getTaskDoneCache() {
		return taskDoneCache;
	}

	public void setTaskDoneCache(TaskDoneCache taskDoneCache) {
		this.taskDoneCache = taskDoneCache;
	}

	public TimeUtil getGlobalTimeClient() {
		return globalTimeClient;
	}

	public void setGlobalTimeClient(TimeUtil globalTimeClient) {
		this.globalTimeClient = globalTimeClient;
	}

	public TrialDrawingController getDrawingController() {
		return drawingController;
	}

	public void setDrawingController(TrialDrawingController drawingController) {
		this.drawingController = drawingController;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

	public TrialContext getCurrentContext() {
		return currentContext;
	}

	public void setCurrentContext(TrialContext currentContext) {
		this.currentContext = currentContext;
	}

	public ExperimentTask getCurrentTask() {
		return currentTask;
	}

	public void setCurrentTask(ExperimentTask currentTask) {
		this.currentTask = currentTask;
	}

	public boolean isAnimation() {
		return isAnimation;
	}

	public void setAnimation(boolean isAnimation) {
		this.isAnimation = isAnimation;
	}

	public int getDelayAfterTrialComplete() {
		return delayAfterTrialComplete;
	}

	public void setDelayAfterTrialComplete(int delayAfterTrialComplete) {
		this.delayAfterTrialComplete = delayAfterTrialComplete;
	}

}

package org.xper.util;

import java.sql.Timestamp;
import java.util.List;

import org.apache.log4j.Logger;
import org.xper.classic.SlideEventListener;
import org.xper.classic.SlideRunner;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.classic.TrialRunner;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.TaskDoneCache;
import org.xper.time.TimeUtil;

public class TrialExperimentUtil {
	static Logger logger = Logger.getLogger(TrialExperimentUtil.class);
	
	public static void cleanupTask (TrialExperimentState stateObject) {
		ExperimentTask currentTask = stateObject.getCurrentTask();
		TaskDataSource taskDataSource = stateObject.getTaskDataSource();
		
		if (currentTask != null) {
			taskDataSource.ungetTask(currentTask);
			currentTask = null;
			stateObject.setCurrentTask(currentTask);
		}
	}
	
	public static TrialResult waitInterSlideInterval (SlideTrialExperimentState stateObject, ThreadHelper threadHelper) {
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		TrialContext currentContext = stateObject.getCurrentContext();
		EyeController eyeController = stateObject.getEyeController();
		
		while (timeUtil.currentTimeMicros() < currentContext.getCurrentSlideOffTime()
				+ stateObject.getInterSlideInterval() * 1000) {
			if (!eyeController.isEyeIn()) {
				TrialExperimentUtil.breakTrial(stateObject);
				return TrialResult.EYE_BREAK;
			}
			if (threadHelper.isDone()) {
				return TrialResult.EXPERIMENT_STOPPING;
			}
		}
		return TrialResult.SLIDE_OK;
	}
	
	/**
	 * Draw the silde.
	 * 
	 * @param i slide index
	 * @param stateObject
	 * @return
	 */
	public static TrialResult doSlide (int i, SlideTrialExperimentState stateObject) {
		TrialDrawingController drawingController = stateObject.getDrawingController();
		ExperimentTask currentTask = stateObject.getCurrentTask();
		TrialContext currentContext = stateObject.getCurrentContext();
		List<? extends SlideEventListener> slideEventListeners = stateObject.getSlideEventListeners();
		EyeController eyeController = stateObject.getEyeController();
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		
		// show current slide
		drawingController.showSlide(currentTask, currentContext);
		long slideOnLocalTime = timeUtil.currentTimeMicros();
		currentContext.setCurrentSlideOnTime(slideOnLocalTime);
		EventUtil.fireSlideOnEvent(i, slideOnLocalTime,
				slideEventListeners);

		// wait for current slide to finish
		do {
			if (!eyeController.isEyeIn()) {
				TrialExperimentUtil.breakTrial(stateObject);
				currentContext.setAnimationFrameIndex(0);
				return TrialResult.EYE_BREAK;
			}
			if (stateObject.isAnimation()) {
				currentContext.setAnimationFrameIndex(currentContext.getAnimationFrameIndex()+1);
				drawingController.animateSlide(currentTask,
						currentContext);
				if (logger.isDebugEnabled()) {
					long t = timeUtil.currentTimeMicros();
					logger.debug(new Timestamp(t/1000).toString() + " " + t % 1000 + " frame: " + currentContext.getAnimationFrameIndex());
				}
			}
		} while (timeUtil.currentTimeMicros() < slideOnLocalTime
				+ stateObject.getSlideLength() * 1000);

		// finish current slide
		drawingController.slideFinish(currentTask, currentContext);
		long slideOffLocalTime = timeUtil.currentTimeMicros();
		currentContext.setCurrentSlideOffTime(slideOffLocalTime);
		EventUtil.fireSlideOffEvent(i, slideOffLocalTime,
						currentContext.getAnimationFrameIndex(),
						slideEventListeners);
		currentContext.setAnimationFrameIndex(0);
		
		return TrialResult.SLIDE_OK;
	}
	
	/**
	 * 
	 * @param stateObject
	 * @param threadHelper
	 * @param runner
	 * @return
	 */
	
	public static TrialResult runTrial (TrialExperimentState stateObject, ThreadHelper threadHelper, SlideRunner runner){
		TrialResult result = TrialExperimentUtil.getMonkeyFixation(stateObject, threadHelper);
		if (result != TrialResult.FIXATION_SUCCESS) {
			return result;
		}

		result = runner.runSlide();
		if (result != TrialResult.TRIAL_COMPLETE) {
			return result;
		}

		TrialExperimentUtil.completeTrial(stateObject, threadHelper);

		return TrialResult.TRIAL_COMPLETE;
	}
	
	/**
	 * If trial fails, the currentTask of TrialExperimentState is not null.
	 * @param state
	 */
	public static void cleanupTrial (TrialExperimentState state) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		ExperimentTask currentTask = state.getCurrentTask();
		TrialContext currentContext = state.getCurrentContext();
		TaskDataSource taskDataSource = state.getTaskDataSource();
		TaskDoneCache taskDoneCache = state.getTaskDoneCache();
		TrialDrawingController drawingController = state.getDrawingController();
		List<? extends TrialEventListener> trialEventListeners = state
		.getTrialEventListeners();
		
		// unget failed task
		if (currentTask != null) {
			taskDataSource.ungetTask(currentTask);
			state.setCurrentTask(null);
		}
		taskDoneCache.flush();

		// trial stop
		if (currentContext != null) {
			long trialStopLocalTime = timeUtil.currentTimeMicros();
			currentContext.setTrialStopTime(trialStopLocalTime);
			drawingController.trialStop(currentContext);
			EventUtil.fireTrialStopEvent(trialStopLocalTime,
					trialEventListeners, currentContext);
		}
		state.setCurrentContext(null);
	}

	/**
	 * 
	 * @param state
	 * @param threadHelper 
	 */
	public static void completeTrial(TrialExperimentState state, ThreadHelper threadHelper) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		TrialContext currentContext = state.getCurrentContext();
		TrialDrawingController drawingController = state.getDrawingController();
		List<? extends TrialEventListener> trialEventListeners = state
		.getTrialEventListeners();
		
		// trial complete here
		long trialCompletedLocalTime = timeUtil.currentTimeMicros();
		currentContext.setTrialCompleteTime(trialCompletedLocalTime);
		drawingController.trialComplete(currentContext);
		EventUtil.fireTrialCompleteEvent(trialCompletedLocalTime,
				trialEventListeners, currentContext);
		
		// wait for delay after trial complete
		if (state.getDelayAfterTrialComplete() > 0) {
			long current = timeUtil.currentTimeMicros();
			ThreadUtil.sleepOrPinUtil(current
						+ state.getDelayAfterTrialComplete() * 1000, state,
						threadHelper);
		}
	}

	/**
	 * Use EyeController to get eye status.
	 * 
	 * @param state
	 * @param threadHelper
	 * @return
	 */
	public static TrialResult getMonkeyFixation(TrialExperimentState state,
			ThreadHelper threadHelper) {
		TrialDrawingController drawingController = state.getDrawingController();
		TrialContext currentContext = state.getCurrentContext();
		TimeUtil timeUtil = state.getLocalTimeUtil();
		List<? extends TrialEventListener> trialEventListeners = state
				.getTrialEventListeners();
		EyeController eyeController = state.getEyeController();
		ExperimentTask currentTask = state.getCurrentTask();
		
		// trial init
		long trialInitLocalTime = timeUtil.currentTimeMicros();
		currentContext.setTrialInitTime(trialInitLocalTime);
		EventUtil.fireTrialInitEvent (trialInitLocalTime, trialEventListeners, currentContext);

		// trial start
		drawingController.trialStart(currentContext);
		long trialStartLocalTime = timeUtil.currentTimeMicros();
		currentContext.setTrialStartTime(trialStartLocalTime);
		EventUtil.fireTrialStartEvent(trialStartLocalTime, trialEventListeners,
				currentContext);

		// prepare fixation point
		drawingController.prepareFixationOn(currentContext);

		// time before fixation point on
		ThreadUtil.sleepOrPinUtil(trialStartLocalTime
				+ state.getTimeBeforeFixationPointOn() * 1000, state,
				threadHelper);

		// fixation point on
		drawingController.fixationOn(currentContext);
		long fixationPointOnLocalTime = timeUtil.currentTimeMicros();
		currentContext.setFixationPointOnTime(fixationPointOnLocalTime);
		EventUtil.fireFixationPointOnEvent(fixationPointOnLocalTime,
				trialEventListeners, currentContext);

		// wait for initial eye in
		boolean success = eyeController
				.waitInitialEyeIn(fixationPointOnLocalTime
						+ state.getTimeAllowedForInitialEyeIn() * 1000);

		if (!success) {
			// eye fail to get in
			long initialEyeInFailLocalTime = timeUtil.currentTimeMicros();
			currentContext.setInitialEyeInFailTime(initialEyeInFailLocalTime);
			drawingController.initialEyeInFail(currentContext);
			EventUtil.fireInitialEyeInFailEvent(initialEyeInFailLocalTime,
					trialEventListeners, currentContext);
			return TrialResult.INITIAL_EYE_IN_FAIL;
		}

		// got initial eye in
		long eyeInitialInLoalTime = timeUtil.currentTimeMicros();
		currentContext.setInitialEyeInTime(eyeInitialInLoalTime);
		EventUtil.fireInitialEyeInSucceedEvent(eyeInitialInLoalTime,
				trialEventListeners, currentContext);

		// prepare first slide
		currentContext.setSlideIndex(0);
		currentContext.setAnimationFrameIndex(0);
		drawingController.prepareFirstSlide(currentTask, currentContext);

		// wait for eye hold
		success = eyeController.waitEyeInAndHold(eyeInitialInLoalTime
				+ state.getRequiredEyeInHoldTime() * 1000);

		if (!success) {
			// eye fail to hold
			long eyeInHoldFailLocalTime = timeUtil.currentTimeMicros();
			currentContext.setEyeInHoldFailTime(eyeInHoldFailLocalTime);
			drawingController.eyeInHoldFail(currentContext);
			EventUtil.fireEyeInHoldFailEvent(eyeInHoldFailLocalTime,
					trialEventListeners, currentContext);
			return TrialResult.EYE_IN_HOLD_FAIL;
		}

		// get fixation, start stimulus
		long eyeHoldSuccessLocalTime = timeUtil.currentTimeMicros();
		currentContext.setFixationSuccessTime(eyeHoldSuccessLocalTime);
		EventUtil.fireFixationSucceedEvent(eyeHoldSuccessLocalTime,
				trialEventListeners, currentContext);

		return TrialResult.FIXATION_SUCCESS;
	}

	public static void checkCurrentTaskAnimation(TrialExperimentState state) {
		state.setAnimation(XmlUtil.slideIsAnimation(state.getCurrentTask()));
	}

	public static void getNextTask(TrialExperimentState state) {
		state.setCurrentTask(state.getTaskDataSource().getNextTask());
	}

	public static void breakTrial(TrialExperimentState state) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		TimeUtil globalTimeClient = state.getGlobalTimeClient();
		TrialContext currentContext = state.getCurrentContext();
		ExperimentTask currentTask = state.getCurrentTask();
		TaskDoneCache taskDoneCache = state.getTaskDoneCache();

		// eye break event
		long eyeInBreakLocalTime = timeUtil.currentTimeMicros();
		currentContext.setEyeInBreakTime(eyeInBreakLocalTime);
		state.getDrawingController().eyeInBreak(currentContext);
		EventUtil.fireEyeInBreakEvent(eyeInBreakLocalTime, state
				.getTrialEventListeners(), currentContext);

		if (currentTask != null) {
			long taskDoneTimestamp = globalTimeClient.currentTimeMicros();
			// save partially show stimulus, don't set currentTask
			// to null so that it will be unget and repeated
			// next time.
			taskDoneCache.put(currentTask, taskDoneTimestamp, true);
		}
	}	

	public static void pauseExperiment(TrialExperimentState state,
			ThreadHelper threadHelper) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		while (state.isPause()) {
			ThreadUtil.sleepOrPinUtil(timeUtil.currentTimeMicros()
					+ TrialExperimentState.EXPERIMENT_PAUSE_SLEEP_INTERVAL * 1000, state,
					threadHelper);
			if (threadHelper.isDone()) {
				return;
			}
		}
	}

	public static void run(TrialExperimentState state,
			ThreadHelper threadHelper, TrialRunner runner) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		try {
			threadHelper.started();
			System.out.println("SlideTrialExperiment started.");

			state.getDrawingController().init();
			EventUtil.fireExperimentStartEvent(timeUtil.currentTimeMicros(),
					state.getExperimentEventListeners());

			while (!threadHelper.isDone()) {
				pauseExperiment(state, threadHelper);
				if (threadHelper.isDone()) {
					break;
				}
				// one trial
				runner.runTrial();
				if (threadHelper.isDone()) {
					break;
				}
				// inter-trial interval
				long current = timeUtil.currentTimeMicros();
				ThreadUtil.sleepOrPinUtil(current
						+ state.getInterTrialInterval() * 1000, state,
						threadHelper);
			}
		} finally {
			// experiment stop event
			try {
				System.out.println("SlideTrialExperiment stopped.");
				EventUtil.fireExperimentStopEvent(timeUtil.currentTimeMicros(),
						state.getExperimentEventListeners());
				state.getDrawingController().destroy();

				threadHelper.stopped();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}
}

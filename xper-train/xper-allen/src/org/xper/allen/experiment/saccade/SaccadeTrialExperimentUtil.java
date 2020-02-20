package org.xper.allen.experiment.saccade;

import java.sql.Timestamp;
import java.util.List;

import org.xper.Dependency;
import org.xper.classic.SlideEventListener;
import org.xper.classic.SlideRunner;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.TaskDoneCache;
import org.xper.eye.EyeMonitor;
import org.xper.eye.EyeTargetSelector;
import org.xper.eye.EyeTargetSelectorConcurrentDriver;
import org.xper.eye.TargetSelectorResult;
import org.xper.time.TimeUtil;
import org.xper.util.EventUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.ThreadUtil;
import org.xper.util.TrialExperimentUtil;
import org.xper.drawing.Coordinates2D;

public class SaccadeTrialExperimentUtil extends TrialExperimentUtil{
	@Dependency
	EyeMonitor eyeMonitor;
	
	public static TrialResult doSlide(int i, SaccadeExperimentState stateObject) {

		
		TrialDrawingController drawingController = stateObject.getDrawingController();
		SaccadeExperimentTask currentTask = stateObject.getCurrentTask();
		SaccadeTrialContext currentContext = (SaccadeTrialContext) stateObject.getCurrentContext();
		List<? extends SlideEventListener> slideEventListeners = stateObject.getSlideEventListeners();
		EyeController eyeController = stateObject.getEyeController();
		EyeTargetSelector targetSelector = stateObject.getTargetSelector();
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		
		
		//show current slide after a delay (blank time)
		
		drawingController.showSlide(currentTask, currentContext);
		long slideOnLocalTime = timeUtil.currentTimeMicros() + stateObject.getBlankTargetScreenDisplayTime()*1000;
		currentContext.setCurrentSlideOnTime(slideOnLocalTime);
		long targetOnLocalTime = currentContext.getCurrentSlideOnTime();
		EventUtil.fireSlideOnEvent(i, slideOnLocalTime, slideEventListeners);
		
		//Eye on Target Logic
		//eye selector
		EyeTargetSelectorConcurrentDriver selectorDriver = new EyeTargetSelectorConcurrentDriver(targetSelector, timeUtil);
		currentContext.setTargetOnTime(currentContext.getCurrentSlideOnTime()); 
		
		
		//Sleep for the duration of the start delay
		//ThreadUtil.sleep(stateObject.getTargetSelectionStartDelay());
		
		//start(Coordinates2D[] targetCenter, double[] targetWinSize, long deadlineIntialEyeIn, long eyeHoldTime)
		selectorDriver.start(new Coordinates2D[] {currentContext.getTargetPos()}, new double[] {currentContext.getTargetEyeWindowSize()},
						     currentContext.getTargetOnTime() + stateObject.getTimeAllowedForInitialTargetSelection()*1000 
						     + stateObject.getTargetSelectionStartDelay() * 1000, stateObject.getRequiredTargetSelectionHoldTime() * 1000);
		do {
		}
		while(!selectorDriver.isDone());
		selectorDriver.stop();
		TargetSelectorResult selectorResult = selectorDriver.getResult();
		System.out.println("SelectionStatusResult = " + selectorResult.getSelectionStatusResult());

		//finish current slide
		drawingController.slideFinish(currentTask, currentContext);
		long slideOffLocalTime = timeUtil.currentTimeMicros();
		currentContext.setCurrentSlideOffTime(slideOffLocalTime);
		EventUtil.fireSlideOffEvent(i, slideOffLocalTime,
		currentContext.getAnimationFrameIndex(),
		slideEventListeners);
		currentContext.setAnimationFrameIndex(0);
		
		return selectorResult.getSelectionStatusResult();
	}

	
	public static TrialResult runTrial (SaccadeExperimentState stateObject, ThreadHelper threadHelper, SlideRunner runner){
		TrialResult result = SaccadeTrialExperimentUtil.getMonkeyFixation(stateObject, threadHelper);
		if (result != TrialResult.FIXATION_SUCCESS) {
			return result;
		}

		result = runner.runSlide();
		if (result != TrialResult.TRIAL_COMPLETE) {
			return result;
		}

		SaccadeTrialExperimentUtil.completeTrial(stateObject, threadHelper);

		return TrialResult.TRIAL_COMPLETE;
	}
	
	public static void cleanupTrial (SaccadeTrialExperimentState state) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		SaccadeExperimentTask currentTask = state.getCurrentTask();
		SaccadeTrialContext currentContext = (SaccadeTrialContext) state.getCurrentContext();
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

	
}

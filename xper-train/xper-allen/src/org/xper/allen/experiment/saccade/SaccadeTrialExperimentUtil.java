package org.xper.allen.experiment.saccade;

import java.util.List;

import org.xper.Dependency;
import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialResult;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.EyeController;
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

	
	public static TrialResult doSlide(int i, SaccadeExperimentState stateObject) {

		
		TrialDrawingController drawingController = stateObject.getDrawingController();
		ExperimentTask currentTask = stateObject.getCurrentTask();
		SaccadeTrialContext currentContext = (SaccadeTrialContext) stateObject.getCurrentContext();
		List<? extends SlideEventListener> slideEventListeners = stateObject.getSlideEventListeners();
		EyeController eyeController = stateObject.getEyeController();
		EyeTargetSelector targetSelector = stateObject.getTargetSelector();
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		

		//show current slide
		drawingController.showSlide(currentTask, currentContext);
		long slideOnLocalTime = timeUtil.currentTimeMicros();
		currentContext.setCurrentSlideOnTime(slideOnLocalTime);
		EventUtil.fireSlideOnEvent(i, slideOnLocalTime, slideEventListeners);
		long targetOnLocalTime = currentContext.getCurrentSlideOnTime();
		
		
		//Eye on Target Logic
		//eye selector
		EyeTargetSelectorConcurrentDriver selectorDriver = new EyeTargetSelectorConcurrentDriver(targetSelector, timeUtil);
		currentContext.setTargetOnTime(targetOnLocalTime); 
		
		//Sleep for the duration of the start delay
		ThreadUtil.sleep(stateObject.getTargetSelectionStartDelay());
		
		//start(Coordinates2D[] targetCenter, double[] targetWinSize, long deadlineIntialEyeIn, long eyeHoldTime)
		selectorDriver.start(new Coordinates2D[] {currentContext.getTargetPos()}, new double[] {currentContext.getTargetEyeWindowSize()},
						     currentContext.getTargetOnTime() + stateObject.getTimeAllowedForInitialTargetSelection()*1000 
						     + stateObject.getTargetSelectionStartDelay() * 1000, stateObject.getRequiredTargetSelectionHoldTime() * 1000);
		
		
		do {
			//While waiting for selection to be done
		}
		while(!selectorDriver.isDone());
		selectorDriver.stop();
		TargetSelectorResult selectorResult = selectorDriver.getResult();
		return selectorResult.getSelectionStatusResult();
	}
	
	
	
	
	public static TrialResult waitInterSlideInterval (SaccadeExperimentState stateObject, ThreadHelper threadHelper) {
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		TrialContext currentContext = stateObject.getCurrentContext();
		EyeController eyeController = stateObject.getEyeController();
		
		while (timeUtil.currentTimeMicros() < currentContext.getCurrentSlideOffTime()
				+ stateObject.getInterSlideInterval() * 1000) {
			if (!eyeController.isEyeIn()) {
				SaccadeTrialExperimentUtil.breakTrial(stateObject);
				return TrialResult.EYE_BREAK;
			}
			if (threadHelper.isDone()) {
				return TrialResult.EXPERIMENT_STOPPING;
			}
		}
		return TrialResult.SLIDE_OK;
	}
}

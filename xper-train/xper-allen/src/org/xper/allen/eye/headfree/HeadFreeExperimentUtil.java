package org.xper.allen.eye.headfree;

import java.util.List;

import org.xper.allen.nafc.experiment.NAFCExperimentState;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCExperimentUtil;
import org.xper.allen.nafc.experiment.NAFCMarkEveryStepTrialDrawingController;
import org.xper.allen.nafc.vo.NAFCTrialResult;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.EyeController;
import org.xper.time.TimeUtil;
import org.xper.util.EventUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.ThreadUtil;

public class HeadFreeExperimentUtil{
	public static NAFCTrialResult getMonkeyFixation(NAFCExperimentState state, ThreadHelper threadHelper) {
		int fixationAttempt = 0;
		int maxFixationAttempts = 5;

		NAFCMarkEveryStepTrialDrawingController drawingController = (NAFCMarkEveryStepTrialDrawingController) state.getDrawingController();

		TrialContext currentContext = state.getCurrentContext();
		TimeUtil timeUtil = state.getLocalTimeUtil();
		List<? extends TrialEventListener> trialEventListeners = state
				.getTrialEventListeners();
		EyeController eyeController = state.getEyeController();
		NAFCExperimentTask currentTask = state.getCurrentTask();

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

		//PREPARING SAMPLE & CHOICE!
		drawingController.prepareSample(currentTask, currentContext); 
		drawingController.prepareChoice(currentTask, currentContext);


		while(fixationAttempt < maxFixationAttempts-1) {
			fixationAttempt++;
			NAFCTrialResult res = getFixationOnly(state, threadHelper, trialStartLocalTime);
			if(res==NAFCTrialResult.FIXATION_SUCCESS) {
				return res;
			} else {
				System.out.println("AC HeadFreeExperimentUtil: FixationAttempt " + fixationAttempt + ". Result: " + res.toString() );
			}
		}
		return NAFCExperimentUtil.getMonkeyFixation(state, threadHelper);
	}

	private static NAFCTrialResult getFixationOnly(NAFCExperimentState state, ThreadHelper threadHelper, long trialStartLocalTime) {
		NAFCMarkEveryStepTrialDrawingController drawingController = (NAFCMarkEveryStepTrialDrawingController) state.getDrawingController();
		TrialContext currentContext = state.getCurrentContext();
		TimeUtil timeUtil = state.getLocalTimeUtil();
		List<? extends TrialEventListener> trialEventListeners = state
				.getTrialEventListeners();
		EyeController eyeController = state.getEyeController();
		NAFCExperimentTask currentTask = state.getCurrentTask();
		
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
			return NAFCTrialResult.INITIAL_EYE_IN_FAIL;
		}

		// got initial eye in
		long eyeInitialInLoalTime = timeUtil.currentTimeMicros();
		currentContext.setInitialEyeInTime(eyeInitialInLoalTime);
		EventUtil.fireInitialEyeInSucceedEvent(eyeInitialInLoalTime,
				trialEventListeners, currentContext);

		// prepare first slide
		currentContext.setSlideIndex(0);
		currentContext.setAnimationFrameIndex(0);
		//drawingController.prepareSample(currentTask, currentContext);

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
			return NAFCTrialResult.EYE_IN_HOLD_FAIL;
		}

		// get fixation, start stimulus
		long eyeHoldSuccessLocalTime = timeUtil.currentTimeMicros();
		currentContext.setFixationSuccessTime(eyeHoldSuccessLocalTime);
		EventUtil.fireFixationSucceedEvent(eyeHoldSuccessLocalTime,
				trialEventListeners, currentContext);

		return NAFCTrialResult.FIXATION_SUCCESS;		
	}
}

package org.xper.allen.nafc.experiment;

import java.io.IOException;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.xper.allen.intan.EStimParameter;
import org.xper.allen.intan.SimpleEStimEventListener;
import org.xper.allen.intan.SimpleEStimEventUtil;
import org.xper.allen.nafc.eye.NAFCEyeTargetSelectorConcurrentDriver;
import org.xper.allen.nafc.eye.NAFCTargetSelectorResult;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.allen.nafc.message.NAFCEventUtil;
import org.xper.allen.nafc.vo.NAFCTrialResult;
import org.xper.allen.saccade.db.vo.EStimObjDataEntry;
import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDoneCache;
import org.xper.eye.EyeTargetSelector;
import org.xper.time.TimeUtil;
import org.xper.util.EventUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.ThreadUtil;
import org.xper.util.TrialExperimentUtil;


import org.xper.util.IntanUtil;

public class NAFCExperimentUtil extends TrialExperimentUtil{
	@SuppressWarnings("incomplete-switch")
	public static NAFCTrialResult doSlide(int i, NAFCExperimentState stateObject) {
		NAFCTrialDrawingController drawingController = (NAFCTrialDrawingController) stateObject.getDrawingController();
		NAFCExperimentTask currentTask = stateObject.getCurrentTask();
		NAFCTrialContext currentContext = (NAFCTrialContext) stateObject.getCurrentContext();
		List<? extends ChoiceEventListener> choiceEventListeners = stateObject.getChoiceEventListeners();
		List<? extends SlideEventListener> slideEventListeners = stateObject.getSlideEventListeners();
		List<? extends SimpleEStimEventListener> eStimEventListeners = stateObject.geteStimEventListeners();
		List<? extends TrialEventListener> trialEventListeners = stateObject.getTrialEventListeners();
		EyeTargetSelector targetSelector = stateObject.getTargetSelector();
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		EyeController eyeController = stateObject.getEyeController();

		boolean fixationSuccess;

		
		NAFCTargetSelectorResult selectorResult;
		//ESTIMULATOR
		/*
		 * EStims are meant to be sent out at the beginning of the trial with time padding added to the EStimSpec in order to match timing
		 * with visual stimuli. 
		 */
		sendEStims(stateObject);
		sendEStimTrigger(stateObject);
		SimpleEStimEventUtil.fireEStimOn(timeUtil.currentTimeMicros(), eStimEventListeners, currentContext);
		System.out.println("EStim Fired");
		
		//show SAMPLE after delay
		long blankOnLocalTime = timeUtil.currentTimeMicros();
		do {
			//do nothing
		}while(timeUtil.currentTimeMicros()<blankOnLocalTime + stateObject.getBlankTargetScreenDisplayTime()*1000);

		//SHOW SAMPLE
		drawingController.prepareSample(currentTask, currentContext);
		drawingController.showSlide(currentTask, currentContext);
		long sampleOnLocalTime = timeUtil.currentTimeMicros();
		currentContext.setCurrentSlideOnTime(sampleOnLocalTime);
		NAFCEventUtil.fireSampleOnEvent(sampleOnLocalTime, choiceEventListeners, currentContext);
		
		//HOLD FIXATION DURING SAMPLE
		fixationSuccess = eyeController.waitEyeInAndHold(sampleOnLocalTime
				+ stateObject.getSampleLength() * 1000 );

		if (!fixationSuccess) {
			// eye fail to hold
			long eyeInHoldFailLocalTime = timeUtil.currentTimeMicros();
			currentContext.setEyeInHoldFailTime(eyeInHoldFailLocalTime);
			drawingController.eyeInHoldFail(currentContext);
			EventUtil.fireEyeInHoldFailEvent(eyeInHoldFailLocalTime,
					trialEventListeners, currentContext);
			return NAFCTrialResult.EYE_IN_HOLD_FAIL;
		}
		long sampleOffLocalTime = timeUtil.currentTimeMicros();
		currentContext.setSampleOffTime(sampleOffLocalTime);
		NAFCEventUtil.fireSampleOffEvent(sampleOffLocalTime, choiceEventListeners, currentContext);
		
		//SHOW CHOICES
		drawingController.prepareChoice(currentTask, currentContext);
		drawingController.showSlide(currentTask, currentContext);
		long choicesOnLocalTime = timeUtil.currentTimeMicros();
		currentContext.setChoicesOnTime(choicesOnLocalTime);
		NAFCEventUtil.fireChoicesOnEvent(choicesOnLocalTime, choiceEventListeners,currentContext);
	

		//Eye on Target Logic
		//eye selector
		NAFCEyeTargetSelectorConcurrentDriver selectorDriver = new NAFCEyeTargetSelectorConcurrentDriver(targetSelector, timeUtil);
		currentContext.setChoicesOnTime(currentContext.getCurrentSlideOnTime()); 


		//SELECTOR START
		selectorDriver.start(currentContext.getTargetPos(), currentContext.getTargetEyeWindowSize(),
				currentContext.getChoicesOnTime() + stateObject.getTimeAllowedForInitialTargetSelection()*1000 
				+ stateObject.getTargetSelectionStartDelay() * 1000, stateObject.getRequiredTargetSelectionHoldTime() * 1000);
		do {
			//Wait for Eye Target Selector To Finish
		}while(!selectorDriver.isDone());
		selectorDriver.stop();
		long choiceDoneLocalTime = timeUtil.currentTimeMicros();
		
		//HANDLING RESULTS
		selectorResult = selectorDriver.getResult();
		NAFCTrialResult result = selectorResult.getSelectionStatusResult();
		int choice = selectorResult.getSelection();
		RewardPolicy rewardPolicy = currentContext.getCurrentTask().getRewardPolicy();
		int[] rewardList = currentContext.getCurrentTask().getRewardList();
		
		switch (result) {
			case TARGET_SELECTION_EYE_FAIL:
				NAFCEventUtil.fireChoiceSelectionEyeFailEvent(choiceDoneLocalTime, choiceEventListeners, currentContext);
				NAFCEventUtil.fireChoiceSelectionNullEvent(choiceDoneLocalTime, choiceEventListeners, currentContext);

				if (rewardPolicy == RewardPolicy.ALWAYS) {
					NAFCEventUtil.fireChoiceSelectionDefaultCorrectEvent(choiceDoneLocalTime, choiceEventListeners);
				}
				if (rewardPolicy == RewardPolicy.NONE) {
					NAFCEventUtil.fireChoiceSelectionCorrectEvent(choiceDoneLocalTime, choiceEventListeners, rewardList);
				}
				break;
				/*
			case TARGET_SELECTION_EYE_BREAK:
				NAFCEventUtil.fireChoiceSelectionEyeBreakEvent(choiceDoneLocalTime, choiceEventListeners, currentContext);
				if (rewardPolicy == RewardPolicy.ANY) {
					NAFCEventUtil.fireChoiceSelectionDefaultCorrectEvent(choiceDoneLocalTime, choiceEventListeners, currentContext);
				}
				if (rewardPolicy == RewardPolicy.NONE) {
					NAFCEventUtil.fireChoiceSelectionCorrectEvent(choiceDoneLocalTime, choiceEventListeners, currentContext);
				}
				break;
				*/
			case TARGET_SELECTION_SUCCESS:
				NAFCEventUtil.fireChoiceSelectionSuccessEvent(choiceDoneLocalTime, choiceEventListeners, choice);
				if (rewardPolicy == RewardPolicy.LIST) {
					if (contains(rewardList, selectorResult.getSelection())) { //if the selector result is contained in the rewardList
						NAFCEventUtil.fireChoiceSelectionCorrectEvent(choiceDoneLocalTime, choiceEventListeners, rewardList);
						System.out.println("Correct Choice");
					}
					else {
						NAFCEventUtil.fireChoiceSelectionIncorrectEvent(choiceDoneLocalTime, choiceEventListeners, rewardList);
						System.out.println("Incorrect Choice");
					}
				}
				if (rewardPolicy == RewardPolicy.ANY) {
					NAFCEventUtil.fireChoiceSelectionDefaultCorrectEvent(choiceDoneLocalTime, choiceEventListeners);
					
				}
				if (rewardPolicy == RewardPolicy.ALWAYS) {
					NAFCEventUtil.fireChoiceSelectionDefaultCorrectEvent(choiceDoneLocalTime, choiceEventListeners);
					
				}				

				break;

		}
		
		System.out.println("SelectionStatusResult = " + selectorResult.getSelectionStatusResult());
		do {
			//Wait for Slide to Finish
		}while(timeUtil.currentTimeMicros()<choicesOnLocalTime+stateObject.getChoiceLength()*1000);
		//finish current slide
		drawingController.trialComplete(currentContext);
		long choiceOffLocalTime = timeUtil.currentTimeMicros();
		currentContext.setChoicesOffTime(choiceOffLocalTime);
		NAFCEventUtil.fireChoicesOffEvent(choiceOffLocalTime, choiceEventListeners, currentContext);
		currentContext.setAnimationFrameIndex(0);


		return selectorResult.getSelectionStatusResult();

	}

	public static boolean contains(final int[] arr, final int key) {
        return Arrays.stream(arr).anyMatch(i -> i == key);
	}
        
	public static NAFCTrialResult runTrial (NAFCExperimentState stateObject, ThreadHelper threadHelper, NAFCSlideRunner runner){
		NAFCTrialResult result = NAFCExperimentUtil.getMonkeyFixation(stateObject, threadHelper);
		if (result != NAFCTrialResult.FIXATION_SUCCESS) {
			return result;
		}

		result = runner.runSlide();
		if (result != NAFCTrialResult.TRIAL_COMPLETE) {
			return result;
		}

		NAFCExperimentUtil.completeTrial(stateObject, threadHelper);

		return NAFCTrialResult.TRIAL_COMPLETE;
	}

	public static void cleanupTrial (NAFCExperimentState state) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		NAFCExperimentTask currentTask = state.getCurrentTask();
		NAFCTrialContext currentContext = (NAFCTrialContext) state.getCurrentContext();
		NAFCDatabaseTaskDataSource taskDataSource = (NAFCDatabaseTaskDataSource) state.getTaskDataSource();
		TaskDoneCache taskDoneCache = state.getTaskDoneCache();
		TrialDrawingController drawingController = state.getDrawingController();
		List<? extends TrialEventListener> trialEventListeners = state
				.getTrialEventListeners();

		// unget failed task
		
		if (currentTask != null) {
			taskDataSource.ungetTask(currentTask);
			
			state.setCurrentTask(null);
		}
		 

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
	 * ESTIMULATOR
	 * Send string of params for estim over to Intan
	 * @param state
	 * @throws Exception 
	 * @throws SQLException 
	 * @throws UnknownHostException 
	 * @throws SocketException 
	 */
	public static void sendEStims (NAFCExperimentState state) {
		try {
		IntanUtil intanUtil = state.getIntanUtil();
		EStimObjDataEntry eStimObjData = state.getCurrentTask().geteStimObjDataEntry();
			//EStimObjDataEntry eStimObjData = state.getCurrentTask().geteStimObjDataEntry();
			System.out.println("Sending EStimSpecs to Intan");
			try {
				intanUtil.send(eStimsToString(eStimObjData));
				System.out.println("EStimSpecs Successfully Sent");
			} catch (IOException e) {
				System.out.println("Cannot Send EStimSpecs");
			}
		}
		catch (NullPointerException e){
		System.out.println("Cannot Send EStims Because There Is No Trial");
		}
	}

	/**
	 * ESTIMULATOR
	 * Send trigger for estim over to Intan
	 * @throws Exception 
	 * @throws SQLException 
	 * @throws UnknownHostException 
	 * @throws SocketException 
	 * 
	 */
	public static void sendEStimTrigger(NAFCExperimentState state){
		IntanUtil intanUtil = state.getIntanUtil();
		System.out.println("Sending Trigger");
		try {
			intanUtil.trigger();	
			System.out.println("Trigger Successfully Sent");
		} catch (Exception e) {
			System.out.println("Cannot Send Trigger");
		}
		
	}
	
	private static String eStimsToString(EStimObjDataEntry eStimObjData){
		ArrayList<EStimParameter> eStimParams= new ArrayList<EStimParameter>();
		eStimParams.add(new EStimParameter("chans",eStimObjData.getChans()));
		eStimParams.add(new EStimParameter("stim_polarity",eStimObjData.get_stim_polarity()));
		eStimParams.add(new EStimParameter("trig_src",eStimObjData.get_trig_src()));
		eStimParams.add(new EStimParameter("stim_shape",eStimObjData.get_stim_shape()));
		eStimParams.add(new EStimParameter("post_trigger_delay",eStimObjData.get_post_trigger_delay()));
		eStimParams.add(new EStimParameter("pulse_repetition",eStimObjData.getPulse_repetition()));
		eStimParams.add(new EStimParameter("num_pulses",eStimObjData.get_num_pulses()));
		eStimParams.add(new EStimParameter("pulse_train_period",eStimObjData.get_pulse_train_period()));
		eStimParams.add(new EStimParameter("post_stim_refractory_period",eStimObjData.get_post_stim_refractory_period()));
		eStimParams.add(new EStimParameter("d1",eStimObjData.get_d1()));
		eStimParams.add(new EStimParameter("d2",eStimObjData.get_d2()));
		eStimParams.add(new EStimParameter("dp",eStimObjData.get_dp()));
		eStimParams.add(new EStimParameter("a1",eStimObjData.get_a1()));
		eStimParams.add(new EStimParameter("a2",eStimObjData.get_a2()));
		eStimParams.add(new EStimParameter("enable_amp_settle",eStimObjData.isEnable_amp_settle()));
		eStimParams.add(new EStimParameter("pre_stim_amp_settle",eStimObjData.get_pre_stim_amp_settle()));
		eStimParams.add(new EStimParameter("post_stim_amp_settle",eStimObjData.get_post_stim_amp_settle()));
		eStimParams.add(new EStimParameter("maintain_amp_settle_during_pulse_train",eStimObjData.get_maintain_amp_settle_during_pulse_train()));
		eStimParams.add(new EStimParameter("enable_charge_recovery",eStimObjData.isEnable_charge_recovery()));
		eStimParams.add(new EStimParameter("post_stim_charge_recovery_on",eStimObjData.get_post_stim_charge_recovery_on()));
		eStimParams.add(new EStimParameter("post_stim_charge_recovery_off",eStimObjData.get_post_stim_charge_recovery_off()));
		
		String output = new String();
		int loopindx = 0;
		for (EStimParameter param:eStimParams) {
			if(loopindx>0) {
				output = output.concat(",");
			}
			output = output.concat(param.getName());
			output = output.concat(",");
			output = output.concat(param.getValue());
			loopindx++;
			
		}
		return output;
	}
	
 
	public static NAFCTrialResult getMonkeyFixation(NAFCExperimentState state,
			ThreadHelper threadHelper) {

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
		drawingController.prepareSample(currentTask, currentContext);

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

	public static void run(NAFCExperimentState state,
			ThreadHelper threadHelper, NAFCTrialRunner runner) {
		TimeUtil timeUtil = state.getLocalTimeUtil();
		try {
			threadHelper.started();
			System.out.println("SlideTrialExperiment started.");
			System.out.println("Trying to get TwoACDrawingController");
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
				//logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}
	
	public static void completeTrial(NAFCExperimentState state, ThreadHelper threadHelper) {
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

}

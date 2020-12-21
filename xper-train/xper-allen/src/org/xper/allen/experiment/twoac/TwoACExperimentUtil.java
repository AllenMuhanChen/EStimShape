package org.xper.allen.experiment.saccade;

import java.io.IOException;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

import org.xper.Dependency;
import org.xper.allen.console.SaccadeEventUtil;
import org.xper.allen.console.TargetEventListener;
import org.xper.allen.db.vo.EStimObjDataEntry;
import org.xper.allen.eye.TwoACEyeTargetSelectorConcurrentDriver;
import org.xper.allen.eye.TwoACTargetSelectorResult;
import org.xper.allen.intan.SimpleEStimEventUtil;
import org.xper.allen.vo.TwoACTrialResult;
import org.xper.classic.SlideEventListener;
import org.xper.classic.SlideRunner;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialResult;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.TaskDoneCache;
import org.xper.eye.EyeMonitor;
import org.xper.eye.EyeTargetSelector;
import org.xper.eye.EyeTargetSelectorConcurrentDriver;
import org.xper.eye.TargetSelectorResult;
import org.xper.time.TimeUtil;
import org.xper.util.EventUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.TrialExperimentUtil;

import jssc.SerialPortException;

import org.xper.util.IntanUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.allen.intan.EStimParameter;
import org.xper.allen.intan.SimpleEStimEventListener;

public class TwoACExperimentUtil extends TrialExperimentUtil{
	public static TrialResult doSlide(int i, SaccadeExperimentState stateObject) {
		TrialDrawingController drawingController = stateObject.getDrawingController();
		SaccadeExperimentTask currentTask = stateObject.getCurrentTask();
		SaccadeTrialContext currentContext = (SaccadeTrialContext) stateObject.getCurrentContext();
		List<? extends SlideEventListener> slideEventListeners = stateObject.getSlideEventListeners();
		List<? extends TargetEventListener> targetEventListeners = stateObject.getTargetEventListeners();
		List<? extends SimpleEStimEventListener> eStimEventListeners = stateObject.geteStimEventListeners();
		EyeTargetSelector targetSelector = stateObject.getTargetSelector();
		TimeUtil timeUtil = stateObject.getLocalTimeUtil();
		

		
		TwoACTargetSelectorResult selectorResult;

		//show current slide after a delay (blank time)
		long blankOnLocalTime = timeUtil.currentTimeMicros();
		do {
			//do nothing
		}while(timeUtil.currentTimeMicros()<blankOnLocalTime + stateObject.getBlankTargetScreenDisplayTime()*1000);

		drawingController.showSlide(currentTask, currentContext);
		long slideOnLocalTime = timeUtil.currentTimeMicros();
		currentContext.setCurrentSlideOnTime(slideOnLocalTime);
		EventUtil.fireSlideOnEvent(i, slideOnLocalTime, slideEventListeners);
		
		//ESTIMULATOR
		sendEStimTrigger(stateObject);
		SimpleEStimEventUtil.fireEStimOn(timeUtil.currentTimeMicros(), eStimEventListeners, currentContext);
		System.out.println("Fired");
		//Eye on Target Logic
		//eye selector
		TwoACEyeTargetSelectorConcurrentDriver selectorDriver = new TwoACEyeTargetSelectorConcurrentDriver(targetSelector, timeUtil);
		currentContext.setTargetOnTime(currentContext.getCurrentSlideOnTime()); 


		//Sleep for the duration of the start delay
		//ThreadUtil.sleep(stateObject.getTargetSelectionStartDelay());

		//start(Coordinates2D[] targetCenter, double[] targetWinSize, long deadlineIntialEyeIn, long eyeHoldTime)
		selectorDriver.start(new Coordinates2D[] {currentContext.getTargetPos()}, new double[] {currentContext.getTargetEyeWindowSize()},
				currentContext.getTargetOnTime() + stateObject.getTimeAllowedForInitialTargetSelection()*1000 
				+ stateObject.getTargetSelectionStartDelay() * 1000, stateObject.getRequiredTargetSelectionHoldTime() * 1000);
		SaccadeEventUtil.fireTargetOnEvent(timeUtil.currentTimeMicros(), targetEventListeners, currentContext);

		do {
			//Wait for Eye Target Selector To Finish
		}while(!selectorDriver.isDone());
		selectorDriver.stop();

		SaccadeEventUtil.fireTargetOffEvent(timeUtil.currentTimeMicros(), targetEventListeners);
		
		selectorResult = selectorDriver.getResult();
		if (selectorResult.getSelectionStatusResult() == TwoACTrialResult.TARGET_SELECTION_EYE_FAIL) {
			SaccadeEventUtil.fireTargetSelectionEyeFailEvent(timeUtil.currentTimeMicros(), targetEventListeners);
		}
		else if (selectorResult.getSelectionStatusResult() == TwoACTrialResult.TARGET_SELECTION_EYE_BREAK) {
			SaccadeEventUtil.fireTargetSelectionEyeBreakEvent(timeUtil.currentTimeMicros(), targetEventListeners);
		}
		//TODO: HANDLE BOTH ONE AND TWO
		else if (selectorResult.getSelectionStatusResult()== TwoACTrialResult.TARGET_SELECTION_ONE) {
			//TODO: New Event Util
			SaccadeEventUtil.fireTargetSelectionDoneEvent(timeUtil.currentTimeMicros(), targetEventListeners);
		}

		System.out.println("SelectionStatusResult = " + selectorResult.getSelectionStatusResult());
		do {
			//Wait for Slide to Finish
		}while(timeUtil.currentTimeMicros()<slideOnLocalTime+stateObject.getSlideLength()*1000);
		//finish current slide
		drawingController.trialComplete(currentContext);
		long slideOffLocalTime = timeUtil.currentTimeMicros();
		currentContext.setCurrentSlideOffTime(slideOffLocalTime);
		EventUtil.fireSlideOffEvent(i, slideOffLocalTime,
				/*
				 * TODO: Animation frame stuff may not be needed 
				 */
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
		sendEStims(stateObject);
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
		AllenDatabaseTaskDataSource taskDataSource = (AllenDatabaseTaskDataSource) state.getTaskDataSource();
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
	public static void sendEStims (SaccadeExperimentState state) {
		try {
		IntanUtil intanUtil = state.getIntanUtil();
		EStimObjDataEntry eStimObjData = state.getCurrentTask().geteStimObjDataEntry();
		System.out.println(eStimsToString(eStimObjData));
			//EStimObjDataEntry eStimObjData = state.getCurrentTask().geteStimObjDataEntry();
			System.out.println("Sending EStimSpecs to Intan");
			System.out.println(eStimsToString(eStimObjData));
			try {
				intanUtil.send(eStimsToString(eStimObjData));
				System.out.println("EStimSpecs Successfully Sent");
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
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
	public static void sendEStimTrigger(SaccadeExperimentState state){
		IntanUtil intanUtil = state.getIntanUtil();
		System.out.println("Sending Trigger");
		try {
			intanUtil.trigger();	
			System.out.println("Trigger Successfully Sent");
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
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
	/*
	private static String addBrackets(String str) {
	 return "{" + str +"}";
	}
	*/

}

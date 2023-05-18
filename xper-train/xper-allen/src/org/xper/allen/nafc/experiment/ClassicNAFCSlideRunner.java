package org.xper.allen.nafc.experiment;

import org.xper.allen.intan.EStimParameter;
import org.xper.allen.intan.EStimEventListener;
import org.xper.allen.intan.SimpleEStimEventUtil;
import org.xper.allen.nafc.eye.NAFCEyeTargetSelectorConcurrentDriver;
import org.xper.allen.nafc.eye.NAFCTargetSelectorResult;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.allen.nafc.message.NAFCEventUtil;
import org.xper.allen.nafc.vo.NAFCTrialResult;
import org.xper.allen.saccade.db.vo.EStimObjDataEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDoneCache;
import org.xper.eye.EyeTargetSelector;
import org.xper.time.TimeUtil;
import org.xper.util.IntanUtil;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.function.IntPredicate;

@SuppressWarnings("StatementWithEmptyBody")
public class ClassicNAFCSlideRunner implements NAFCSlideRunner {
    private int punishmentDelayTime = 0; //Gets initialized to 0, if punishment should be applied, it's incremented, reset to zero after trial interval.

    public NAFCTrialResult runSlide(NAFCExperimentState stateObject, NAFCTrialContext context) {
            NAFCExperimentTask currentTask = stateObject.getCurrentTask();
            TaskDoneCache taskDoneCache = stateObject.getTaskDoneCache();
            TimeUtil globalTimeClient = stateObject.getGlobalTimeClient();
        NAFCTrialResult result;

            try {
                try {
                    //target info -AC
                    retrieveTargetInformation(context);
                } catch (Exception e){
                    return noMoreTrials();
                }


                // draw the slide
                result = doSlide(stateObject);

                //Check if Sample Hold was Successful
                if (sampleHoldSuccessful(result)){
                    return result;
                }

                // Trial done successfully
                if (currentTask != null) {
                    taskDone(stateObject, currentTask, taskDoneCache, globalTimeClient);
                }

                return NAFCTrialResult.TRIAL_COMPLETE;

            } finally {
                try {
                    cleanupTask(stateObject);
                } catch (Exception e) {
//                    logger.warn(e.getMessage());
                    e.printStackTrace();
                }
            }
        }

    private void taskDone(NAFCExperimentState stateObject, NAFCExperimentTask currentTask, TaskDoneCache taskDoneCache, TimeUtil globalTimeClient) {
        taskDoneCache.put(currentTask, globalTimeClient
                .currentTimeMicros(), false);
        stateObject.setCurrentTask(null);
    }

    private boolean sampleHoldSuccessful(NAFCTrialResult result) {
        return result != NAFCTrialResult.TRIAL_COMPLETE;
    }

    private NAFCTrialResult noMoreTrials() {
        System.out.println("No More Trials");
        try {
            Thread.sleep(NAFCTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
        } catch (InterruptedException ignored) {
        }
        return NAFCTrialResult.NO_MORE_TASKS;
    }

    private void retrieveTargetInformation(NAFCTrialContext context) {
        Coordinates2D[] targetPosition = context.getCurrentTask().getTargetEyeWinCoords();
        double[] targetEyeWinSize = context.getCurrentTask().getTargetEyeWinSize();
        context.setTargetPos(targetPosition);
        context.setTargetEyeWindowSize(targetEyeWinSize);
    }

    public NAFCTrialResult doSlide(NAFCExperimentState stateObject) {
        NAFCTrialDrawingController drawingController = stateObject.getDrawingController();
        NAFCExperimentTask currentTask = stateObject.getCurrentTask();
        NAFCTrialContext currentContext = stateObject.getCurrentContext();
        List<? extends ChoiceEventListener> choiceEventListeners = stateObject.getChoiceEventListeners();
        List<? extends EStimEventListener> eStimEventListeners = stateObject.geteStimEventListeners();
        EyeTargetSelector targetSelector = stateObject.getTargetSelector();
        TimeUtil timeUtil = stateObject.getLocalTimeUtil();
        EyeController eyeController = stateObject.getEyeController();
        NAFCDatabaseTaskDataSource taskDataSource = (NAFCDatabaseTaskDataSource) stateObject.getTaskDataSource();


        NAFCTargetSelectorResult selectorResult;


        //ESTIMULATOR
        /*
         * EStims are meant to be sent out at the beginning of the trial with time padding added to the EStimSpec in order to match timing
         * with visual stimuli.
         */
//        sendEStims(stateObject);
//        sendEStimTrigger(stateObject);
        SimpleEStimEventUtil.prepareEStim(timeUtil.currentTimeMicros(), eStimEventListeners, currentContext);

        //show SAMPLE after delay
        long blankOnLocalTime = timeUtil.currentTimeMicros();
        do {
            //do nothing
        }while(timeUtil.currentTimeMicros()<blankOnLocalTime + stateObject.getBlankTargetScreenDisplayTime()* 1000L);

        //SHOW SAMPLE
        SimpleEStimEventUtil.fireEStimOn(timeUtil.currentTimeMicros(), eStimEventListeners, currentContext);
        System.out.println("EStim Fired");
        drawingController.showSample(currentTask, currentContext); //THIS is called by prepare fixation
        long sampleOnLocalTime = timeUtil.currentTimeMicros();
        currentContext.setSampleOnTime(sampleOnLocalTime);
//		currentContext.setCurrentSlideOnTime(sampleOnLocalTime);
        NAFCEventUtil.fireSampleOnEvent(sampleOnLocalTime, choiceEventListeners, currentContext);

        //HOLD FIXATION DURING SAMPLE
        do {
            if(!eyeController.isEyeIn()) {
                long eyeInHoldFailLocalTime = timeUtil.currentTimeMicros();
                currentContext.setEyeInHoldFailTime(eyeInHoldFailLocalTime);
                drawingController.eyeInHoldFail(currentContext);
                NAFCEventUtil.fireSampleEyeInHoldFail(eyeInHoldFailLocalTime,
                        choiceEventListeners, currentContext);
                punish(stateObject);

                drawingController.slideFinish(currentTask, currentContext);
                long sampleOffLocalTime = timeUtil.currentTimeMicros();
                currentContext.setSampleOffTime(sampleOffLocalTime);
                NAFCEventUtil.fireSampleOffEvent(sampleOffLocalTime, choiceEventListeners, currentContext);

                if (stateObject.isRepeatIncorrectTrials()) {
                    taskDataSource.ungetTask(currentTask);
                    System.out.println("Repeating Incorrect Trial");
                }

                //AC: 03/27/2022. Changed this to Trial_Complete so if this fails, the trial is over. Animal Doesn't get a second chance.
                return NAFCTrialResult.TRIAL_COMPLETE;
            }
			if(stateObject.isAnimation()) {
                currentContext.setAnimationFrameIndex(currentContext.getAnimationFrameIndex()+1);
                drawingController.animateSample(currentTask, currentContext);
            }
        } while (timeUtil.currentTimeMicros() < sampleOnLocalTime
                + stateObject.getSampleLength() * 1000L);


        //		fixationSuccess = eyeController.waitEyeInAndHold(sampleOnLocalTime
//				+ stateObject.getSampleLength() * 1000 );

//		if (!fixationSuccess) {
//			// eye fail to hold
//			long eyeInHoldFailLocalTime = timeUtil.currentTimeMicros();
//			currentContext.setEyeInHoldFailTime(eyeInHoldFailLocalTime);
//			drawingController.eyeInHoldFail(currentContext);
//			NAFCEventUtil.fireSampleEyeInHoldFail(eyeInHoldFailLocalTime,
//					choiceEventListeners, currentContext);
//
//			drawingController.slideFinish(currentTask, currentContext);
//			long sampleOffLocalTime = timeUtil.currentTimeMicros();
//			currentContext.setSampleOffTime(sampleOffLocalTime);
//			NAFCEventUtil.fireSampleOffEvent(sampleOffLocalTime, choiceEventListeners, currentContext);
//
//			//AC: 03/27/2022. Changed this to Trial_Complete so if this fails, the trial is over. Animal Doesn't get a second chance.
//			return NAFCTrialResult.TRIAL_COMPLETE;
//		}
        drawingController.slideFinish(currentTask, currentContext);
        long sampleOffLocalTime = timeUtil.currentTimeMicros();
        currentContext.setSampleOffTime(sampleOffLocalTime);
        NAFCEventUtil.fireSampleOffEvent(sampleOffLocalTime, choiceEventListeners, currentContext);
        currentContext.setAnimationFrameIndex(0);


        //SHOW CHOICES
//		drawingController.prepareChoice(currentTask, currentContext);
        drawingController.showChoice(currentTask, currentContext);
        long choicesOnLocalTime = timeUtil.currentTimeMicros();
        currentContext.setChoicesOnTime(choicesOnLocalTime);
        NAFCEventUtil.fireChoicesOnEvent(choicesOnLocalTime, choiceEventListeners,currentContext);


        //Eye on Target Logic
        //eye selector
        NAFCEyeTargetSelectorConcurrentDriver selectorDriver = new NAFCEyeTargetSelectorConcurrentDriver(targetSelector, timeUtil);
        currentContext.setChoicesOnTime(currentContext.getChoicesOnTime());


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
        long choicesOffLocalTime = timeUtil.currentTimeMicros();
        NAFCEventUtil.fireChoicesOffEvent(choicesOffLocalTime, choiceEventListeners, currentContext);
        selectorResult = selectorDriver.getResult();
        NAFCTrialResult result = selectorResult.getSelectionStatusResult();
        int choice = selectorResult.getSelection();
        RewardPolicy rewardPolicy = currentContext.getCurrentTask().getRewardPolicy();
        int[] rewardList = currentContext.getCurrentTask().getRewardList();


        switch (result) {
            case TARGET_SELECTION_EYE_FAIL:

                NAFCEventUtil.fireChoiceSelectionNullEvent(choiceDoneLocalTime, choiceEventListeners, currentContext);

                if (rewardPolicy == RewardPolicy.ALWAYS) {
                    NAFCEventUtil.fireChoiceSelectionDefaultCorrectEvent(choiceDoneLocalTime, choiceEventListeners);
                }
                if (rewardPolicy == RewardPolicy.NONE) {
                    NAFCEventUtil.fireChoiceSelectionCorrectEvent(choiceDoneLocalTime, choiceEventListeners, rewardList);
                }
                else {
                    NAFCEventUtil.fireChoiceSelectionEyeFailEvent(choiceDoneLocalTime, choiceEventListeners, currentContext);
                    return NAFCTrialResult.TARGET_SELECTION_EYE_FAIL;
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
                        resetPunishment();
                        System.out.println("Correct Choice");
                    }
                    else {
                        NAFCEventUtil.fireChoiceSelectionIncorrectEvent(choiceDoneLocalTime, choiceEventListeners, rewardList);
                        //PUNISHMENT DELAY
                        punish(stateObject);

                        if (stateObject.isRepeatIncorrectTrials()) {
                            taskDataSource.ungetTask(currentTask);
                            System.out.println("Repeating Incorrect Trial");
                        }
                        System.out.println("Incorrect Choice");
                    }
                }
                if (rewardPolicy == RewardPolicy.ANY) {
                    if (contains(rewardList, selectorResult.getSelection())) { //if the selector result is contained in the rewardList
                        NAFCEventUtil.fireChoiceSelectionCorrectEvent(choiceDoneLocalTime, choiceEventListeners, rewardList);
                        System.out.println("Correct Choice");
                    }
                    else {
                        NAFCEventUtil.fireChoiceSelectionDefaultCorrectEvent(choiceDoneLocalTime, choiceEventListeners);
                        System.out.println("Incorrect Choice - Rewarded by Default");
                    }
                }
                if (rewardPolicy == RewardPolicy.ALWAYS) {
                    if (contains(rewardList, selectorResult.getSelection())) { //if the selector result is contained in the rewardList
                        NAFCEventUtil.fireChoiceSelectionCorrectEvent(choiceDoneLocalTime, choiceEventListeners, rewardList);
                        System.out.println("Correct Choice");
                    }
                    else {
                        NAFCEventUtil.fireChoiceSelectionDefaultCorrectEvent(choiceDoneLocalTime, choiceEventListeners);
                        System.out.println("Incorrect Choice - Rewarded by Default");
                    }
                }

                break;

        }

        System.out.println("SelectionStatusResult = " + selectorResult.getSelectionStatusResult());
        if(stateObject.isShowAnswer()) {
            drawingController.showAnswer(currentTask, currentContext);
            do {
                //Wait for Slide to Finish
                //Currently choiceLength is like a minimum time the choice must be on. The choice can be on for longer.
            } while (timeUtil.currentTimeMicros() < choicesOffLocalTime + stateObject.getAnswerLength() * 1000L);
        }
        //finish current slide



        drawingController.trialComplete(currentContext);
        long choiceOffLocalTime = timeUtil.currentTimeMicros();
        currentContext.setChoicesOffTime(choiceOffLocalTime);
        NAFCEventUtil.fireChoicesOffEvent(choiceOffLocalTime, choiceEventListeners, currentContext);
        currentContext.setAnimationFrameIndex(0);

        return NAFCTrialResult.TRIAL_COMPLETE;

    }

    public static boolean contains(final int[] arr, final int key) {
        return Arrays.stream(arr).anyMatch(new IntPredicate() {
            @Override
            public boolean test(int value) {
                return value == key;
            }
        });
    }

//    /**
//     * ESTIMULATOR
//     * Send string of params for estim over to Intan
//     */
//    public void sendEStims (NAFCExperimentState state) {
//        try {
//            IntanUtil intanUtil = state.getIntanUtil();
//            EStimObjDataEntry eStimObjData = state.getCurrentTask().geteStimSpec();
//            //EStimObjDataEntry eStimObjData = state.getCurrentTask().geteStimObjDataEntry();
//            System.out.println("Sending EStimSpecs to Intan");
//            try {
//                intanUtil.send(eStimsToString(eStimObjData));
//                System.out.println("EStimSpecs Successfully Sent");
//            } catch (IOException e) {
//                System.out.println("Cannot Send EStimSpecs");
//            }
//        }
//        catch (NullPointerException e){
//            System.out.println("Cannot Send EStims Because There Is No Trial");
//        }
//    }

    private String eStimsToString(EStimObjDataEntry eStimObjData){
        ArrayList<EStimParameter> eStimParams= new ArrayList<>();
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

        String output = "";
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

    /**
     * ESTIMULATOR
     * Send trigger for estim over to Intan
     *
     */
    public void sendEStimTrigger(NAFCExperimentState state){
        IntanUtil intanUtil = state.getIntanUtil();
        System.out.println("Sending Trigger");
        try {
            intanUtil.trigger();
            System.out.println("Trigger Successfully Sent");
        } catch (Exception e) {
            System.out.println("Cannot Send Trigger");
        }

    }

    private void resetPunishment() {
        setPunishmentDelayTime(0);
    }

    private void punish(NAFCExperimentState stateObject) {
        if(getPunishmentDelayTime() ==0) {
            setPunishmentDelayTime(stateObject.getPunishmentDelayTime());
        }
    }

    public void cleanupTask(NAFCExperimentState stateObject) {
        NAFCExperimentTask currentTask = stateObject.getCurrentTask();
        NAFCDatabaseTaskDataSource taskDataSource = (NAFCDatabaseTaskDataSource) stateObject.getTaskDataSource();

        if (currentTask != null) {
            taskDataSource.ungetTask(currentTask);
            currentTask = null;
            stateObject.setCurrentTask(currentTask);
        }
    }

    public int getPunishmentDelayTime() {
        return punishmentDelayTime;
    }

    public void setPunishmentDelayTime(int punishmentDelayTime) {
        this.punishmentDelayTime = punishmentDelayTime;
    }
}
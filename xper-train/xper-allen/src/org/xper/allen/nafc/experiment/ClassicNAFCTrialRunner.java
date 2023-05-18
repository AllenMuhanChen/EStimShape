package org.xper.allen.nafc.experiment;

import org.dom4j.Document;
import org.xper.Dependency;
import org.xper.allen.nafc.vo.NAFCTrialResult;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDoneCache;
import org.xper.time.TimeUtil;
import org.xper.util.*;

import java.util.List;

public class ClassicNAFCTrialRunner implements NAFCTrialRunner{

    @Dependency
    ClassicNAFCTaskRunner runner;

    public NAFCTrialResult runTrial(NAFCExperimentState stateObject, ThreadHelper threadHelper) {
        try {
            // get a task
            getNextTask(stateObject);
            NAFCTrialResult noMoreTasks = checkForNoMoreTasks(stateObject);
            if (noMoreTasks != null) return noMoreTasks;

            // initialize trial context
            NAFCTrialContext context = intializeTrialContext(stateObject);

            /*
              If switch out HeadFreeUtil then make sure the new version has prepareSample & prepareChoice
             */
            NAFCTrialResult result = getMonkeyFixation(stateObject, threadHelper);
            if (result != NAFCTrialResult.FIXATION_SUCCESS) {
                return result;
            }

            //Run NAFC Task
            result = getRunner().runTask(stateObject, context);
            if (result != NAFCTrialResult.TRIAL_COMPLETE) {
                return result;
            }

            //Complete Trial
            completeTrial(stateObject, threadHelper);

            return NAFCTrialResult.TRIAL_COMPLETE;
        } finally {
            try {
                cleanupTrial(stateObject);
            } catch (Exception e) {
//                    logger.warn(e.getMessage());
                e.printStackTrace();
            }
        }
    }

    private NAFCTrialContext intializeTrialContext(NAFCExperimentState stateObject) {
        NAFCTrialContext context = new NAFCTrialContext();
        context.setCurrentTask(stateObject.getCurrentTask());
        stateObject.setCurrentContext(context);
        stateObject.getCurrentContext().setCurrentTask(stateObject.getCurrentTask());
        context.setSampleLength(stateObject.getSampleLength());
        checkCurrentTaskAnimation(stateObject);
        return context;
    }

    public void checkCurrentTaskAnimation(NAFCExperimentState state) {
        state.setAnimation(isAnimation(state.getCurrentTask().getSampleSpec()));
    }

    public static boolean isAnimation(String xml) {
        Document doc = XmlUtil.parseSpec(xml);
        return XmlUtil.isAnimation(doc, "/StimSpec");
    }


    private NAFCTrialResult checkForNoMoreTasks(NAFCExperimentState stateObject) {
        if (stateObject.getCurrentTask() == null && !stateObject.isDoEmptyTask()) {
            try {
                Thread.sleep(SlideTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
            } catch (InterruptedException ignored) {
            }
            return NAFCTrialResult.NO_MORE_TASKS;
        }
        return null;
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
        long current = timeUtil.currentTimeMicros();
        if (state.getDelayAfterTrialComplete() > 0) {
            ThreadUtil.sleepOrPinUtil(current
                            + state.getDelayAfterTrialComplete() * 1000L, state,
                    threadHelper);
        }
    }


    public static void getNextTask(NAFCExperimentState state) {
        state.setCurrentTask(state.getTaskDataSource().getNextTask());
    }

    public static void cleanupTrial (NAFCExperimentState state) {
        TimeUtil timeUtil = state.getLocalTimeUtil();
        NAFCExperimentTask currentTask = state.getCurrentTask();
        NAFCTrialContext currentContext = state.getCurrentContext();
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

    public NAFCTrialResult getMonkeyFixation(NAFCExperimentState state,
                                             ThreadHelper threadHelper) {

        NAFCTrialDrawingController drawingController = state.getDrawingController();
        NAFCTrialContext currentContext = state.getCurrentContext();
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

        //Prepare Sample & Choice!
        drawingController.prepareSample(currentTask, currentContext);
        drawingController.prepareChoice(currentTask, currentContext);

        // prepare fixation point
        drawingController.prepareFixationOn(currentContext);

        // time before fixation point on
        ThreadUtil.sleepOrPinUtil(trialStartLocalTime
                        + state.getTimeBeforeFixationPointOn() * 1000L, state,
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
                        + state.getTimeAllowedForInitialEyeIn() * 1000L);

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
                + state.getRequiredEyeInHoldTime() * 1000L + getRunner().getPunishmentDelayTime()* 1000L);


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

    public ClassicNAFCTaskRunner getRunner() {
        return runner;
    }

    public void setRunner(ClassicNAFCTaskRunner runner) {
        this.runner = runner;
    }
}
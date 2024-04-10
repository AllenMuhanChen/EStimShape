package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.classic.*;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.TaskDoneCache;
import org.xper.time.TimeUtil;
import org.xper.util.EventUtil;
import org.xper.util.ThreadHelper;

import java.util.List;

public class MockSlideTrialRunner implements SlideTrialRunner{

    @Dependency
    SlideRunner slideRunner;

    @Override
    public TrialResult runTrial(SlideTrialExperimentState stateObject, ThreadHelper threadHelper) {
        try {
            ClassicSlideRunner.getNextTask(stateObject);

            if (stateObject.getCurrentTask() == null && !stateObject.isDoEmptyTask()) {
                try {
                    Thread.sleep(SlideTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
                } catch (InterruptedException e) {
                }
                return TrialResult.NO_MORE_TASKS;
            }

            // initialize trial context
            stateObject.setCurrentContext(new TrialContext());
            stateObject.getCurrentContext().setCurrentTask(stateObject.getCurrentTask());


            TrialResult result = getMonkeyFixation(stateObject, threadHelper);
            if (result != TrialResult.FIXATION_SUCCESS) {
                return result;
            }

            result = slideRunner.runSlides(stateObject, threadHelper);
            if (result != TrialResult.TRIAL_COMPLETE) {
                return result;
            }

            completeTrial(stateObject, threadHelper);

            return TrialResult.TRIAL_COMPLETE;
        } finally {
            try {
                cleanupTrial(stateObject);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

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
//            drawingController.trialStop(currentContext);
            EventUtil.fireTrialStopEvent(trialStopLocalTime,
                    trialEventListeners, currentContext);
        }
        state.setCurrentContext(null);
    }


    public static void completeTrial(TrialExperimentState state, ThreadHelper threadHelper) {
        TimeUtil timeUtil = state.getLocalTimeUtil();
        TrialContext currentContext = state.getCurrentContext();
        TrialDrawingController drawingController = state.getDrawingController();
        List<? extends TrialEventListener> trialEventListeners = state
                .getTrialEventListeners();

        // trial complete here
        long trialCompletedLocalTime = timeUtil.currentTimeMicros();
        currentContext.setTrialCompleteTime(trialCompletedLocalTime);
//        drawingController.trialComplete(currentContext);
        EventUtil.fireTrialCompleteEvent(trialCompletedLocalTime,
                trialEventListeners, currentContext);

//        // wait for delay after trial complete
//        if (state.getDelayAfterTrialComplete() > 0) {
//            long current = timeUtil.currentTimeMicros();
//            ThreadUtil.sleepOrPinUtil(current
//                            + state.getDelayAfterTrialComplete() * 1000, state,
//                    threadHelper);
//        }
    }


    private TrialResult getMonkeyFixation(TrialExperimentState state, ThreadHelper threadHelper) {
        TimeUtil timeUtil = state.getLocalTimeUtil();
        TrialContext currentContext = state.getCurrentContext();
        List<? extends TrialEventListener> trialEventListeners = state
                .getTrialEventListeners();

        // trial init
        long trialInitLocalTime = timeUtil.currentTimeMicros();
        currentContext.setTrialInitTime(trialInitLocalTime);
        EventUtil.fireTrialInitEvent (trialInitLocalTime, trialEventListeners, currentContext);
        // trial start
        long trialStartLocalTime = timeUtil.currentTimeMicros();
        currentContext.setTrialStartTime(trialStartLocalTime);
        EventUtil.fireTrialStartEvent(trialStartLocalTime, trialEventListeners,
                currentContext);
        // got initial eye in
        long eyeInitialInLoalTime = timeUtil.currentTimeMicros();
        currentContext.setInitialEyeInTime(eyeInitialInLoalTime);
        EventUtil.fireInitialEyeInSucceedEvent(eyeInitialInLoalTime,
                trialEventListeners, currentContext);
        // get fixation, start stimulus
        long eyeHoldSuccessLocalTime = timeUtil.currentTimeMicros();
        currentContext.setFixationSuccessTime(eyeHoldSuccessLocalTime);
        EventUtil.fireFixationSucceedEvent(eyeHoldSuccessLocalTime,
                trialEventListeners, currentContext);

        return TrialResult.FIXATION_SUCCESS;
    }


    public SlideRunner getSlideRunner() {
        return slideRunner;
    }

    public void setSlideRunner(SlideRunner slideTrialRunner) {
        this.slideRunner = slideTrialRunner;
    }
}
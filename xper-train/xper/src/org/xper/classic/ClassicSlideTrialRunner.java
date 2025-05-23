package org.xper.classic;

import org.xper.Dependency;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.drawing.AbstractTaskScene;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.TaskDoneCache;
import org.xper.time.TimeUtil;
import org.xper.util.*;

import java.util.List;

import static org.xper.classic.ClassicSlideRunner.breakTrial;

public class ClassicSlideTrialRunner implements SlideTrialRunner {

    @Dependency
    ClassicSlideRunner slideRunner;

    @Dependency
    Punisher punisher;

    public TrialResult runTrial(SlideTrialExperimentState stateObject, ThreadHelper threadHelper) {
        try {
            // get a task
            getNextTask(stateObject);

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
            checkCurrentTaskAnimation(stateObject);

            // Get monkey fixation
            TrialResult result = getMonkeyFixation(stateObject, threadHelper);
            if (result != TrialResult.FIXATION_SUCCESS) {
                return result;
            }

            // wait ISI before first slide
            TimeUtil timeUtil = stateObject.getLocalTimeUtil();
            TrialContext currentContext = stateObject.getCurrentContext();
            EyeController eyeController = stateObject.getEyeController();

            while (timeUtil.currentTimeMicros() < currentContext.getFixationSuccessTime()
                    + stateObject.getInterSlideInterval() * 1000L) {
                if (!eyeController.isEyeIn()) {
                    breakTrial(stateObject);
                    return TrialResult.EYE_BREAK;
                }
                if (threadHelper.isDone()) {
                    return TrialResult.EXPERIMENT_STOPPING;
                }
            }

            result = slideRunner.runSlides(stateObject, threadHelper);
            if (result != TrialResult.TRIAL_COMPLETE) {
                punisher.punish();
                return result;
            }
            punisher.resetPunishment();
            completeTrial(stateObject, threadHelper);

            return TrialResult.TRIAL_COMPLETE;

            // end of TrialRunner.runTrial
        } finally {
            try {
                cleanupTrial(stateObject);
            } catch (Exception e) {
                SlideTrialExperiment.logger.warn(e.getMessage());
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

    public void checkCurrentTaskAnimation(TrialExperimentState state) {
        state.setAnimation(XmlUtil.slideIsAnimation(state.getCurrentTask()));
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

    public TrialResult getMonkeyFixation(TrialExperimentState state,
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

        switchFixationIfPunishment(drawingController);

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
                        + state.getTimeAllowedForInitialEyeIn() * 1000L);

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
        long eyeInitialInLocalTime = timeUtil.currentTimeMicros();
        currentContext.setInitialEyeInTime(eyeInitialInLocalTime);
        EventUtil.fireInitialEyeInSucceedEvent(eyeInitialInLocalTime,
                trialEventListeners, currentContext);

        // prepare first slide
        currentContext.setSlideIndex(0);
        currentContext.setAnimationFrameIndex(0);
        drawingController.prepareFirstSlide(currentTask, currentContext);

        // wait for eye hold
        System.err.println("Punishment time: " + punisher.getCurrentPunishmentTime());
        success = eyeController.waitEyeInAndHold(eyeInitialInLocalTime
                + state.getRequiredEyeInHoldTime() * 1000L + punisher.getCurrentPunishmentTime() * 1000L);

        if (!success) {
            // eye fail to hold
            long eyeInHoldFailLocalTime = timeUtil.currentTimeMicros();
            currentContext.setEyeInHoldFailTime(eyeInHoldFailLocalTime);
            drawingController.eyeInHoldFail(currentContext);
            EventUtil.fireEyeInHoldFailEvent(eyeInHoldFailLocalTime,
                    trialEventListeners, currentContext);
            return TrialResult.EYE_IN_HOLD_FAIL;
        }

        // get fixation
        long eyeHoldSuccessLocalTime = timeUtil.currentTimeMicros();
        currentContext.setFixationSuccessTime(eyeHoldSuccessLocalTime);
        EventUtil.fireFixationSucceedEvent(eyeHoldSuccessLocalTime,
                trialEventListeners, currentContext);

        // if this was a punished fixation, reset punishment if successful
        if (punisher.getCurrentPunishmentTime() > 0) {
            punisher.resetPunishment();
        }
        return TrialResult.FIXATION_SUCCESS;
    }


    private void switchFixationIfPunishment(TrialDrawingController drawingController) {
        // modify fixation point if punishment is on
        AbstractTaskScene taskScene = (AbstractTaskScene) drawingController.getTaskScene();
        if (punisher.getCurrentPunishmentTime() > 0) {
            taskScene.setFixation(punisher.getPunishmentFixationPoint());
        } else{
            taskScene.setFixation(punisher.getOriginalFixationPoint());
        }
    }

    public static void getNextTask(TrialExperimentState state) {
        state.setCurrentTask(state.getTaskDataSource().getNextTask());
    }

    public ClassicSlideRunner getSlideRunner() {
        return slideRunner;
    }

    public void setSlideRunner(ClassicSlideRunner slideRunner) {
        this.slideRunner = slideRunner;
    }

    public void setPunisher(Punisher punisher) {
        this.punisher = punisher;
    }
}
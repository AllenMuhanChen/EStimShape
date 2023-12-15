package org.xper.classic;

import org.xper.Dependency;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.TaskDoneCache;
import org.xper.time.TimeUtil;
import org.xper.util.EventUtil;
import org.xper.util.ThreadHelper;
import org.xper.util.XmlUtil;

import java.sql.Timestamp;
import java.util.List;

import static org.xper.classic.SlideTrialExperiment.logger;

public class ClassicSlideRunner implements SlideRunner {

    @Dependency
    Punisher punisher;

    public TrialResult runSlide(SlideTrialExperimentState stateObject, ThreadHelper threadHelper) {
        int slidePerTrial = stateObject.getSlidePerTrial();
        TrialDrawingController drawingController = stateObject.getDrawingController();
        ExperimentTask currentTask = stateObject.getCurrentTask();
        TrialContext currentContext = stateObject.getCurrentContext();
        TaskDoneCache taskDoneCache = stateObject.getTaskDoneCache();
        TimeUtil globalTimeClient = stateObject.getGlobalTimeClient();

        try {
            for (int i = 0; i < slidePerTrial; i++) {

                // draw the slide
                TrialResult result = doSlide(i, stateObject);
                if (result != TrialResult.SLIDE_OK) {
                    return result;
                }

                // slide done successfully
                if (currentTask != null) {
                    taskDoneCache.put(currentTask, globalTimeClient
                            .currentTimeMicros(), false);
                    currentTask = null;
                    stateObject.setCurrentTask(currentTask);
                }

                // prepare next task
                if (i < slidePerTrial - 1) {
                    getNextTask(stateObject);
                    currentTask = stateObject.getCurrentTask();
                    if (currentTask == null && !stateObject.isDoEmptyTask()) {
                        try {
                            Thread.sleep(SlideTrialExperimentState.NO_TASK_SLEEP_INTERVAL);
                        } catch (InterruptedException e) {
                        }
                        //return TrialResult.NO_MORE_TASKS;
                        //deliver juice after complete.
                        return TrialResult.TRIAL_COMPLETE;
                    }
                    stateObject.setAnimation(XmlUtil.slideIsAnimation(currentTask));
                    currentContext.setSlideIndex(i + 1);
                    currentContext.setCurrentTask(currentTask);
                    drawingController.prepareNextSlide(currentTask,
                            currentContext);
                }
                // inter slide interval
                result = waitInterSlideInterval(stateObject, threadHelper);
                if (result != TrialResult.SLIDE_OK) {
                    return result;
                }
            }
            punisher.resetPunishment();
            return TrialResult.TRIAL_COMPLETE;
            // end of SlideRunner.runSlide
        } finally {
            try {
                cleanupTask(stateObject);
            } catch (Exception e) {
                logger.warn(e.getMessage());
                e.printStackTrace();
            }
        }
    }

    public static void cleanupTask (TrialExperimentState stateObject) {
        ExperimentTask currentTask = stateObject.getCurrentTask();
        TaskDataSource taskDataSource = stateObject.getTaskDataSource();

        if (currentTask != null) {
            taskDataSource.ungetTask(currentTask);
            currentTask = null;
            stateObject.setCurrentTask(currentTask);
        }
    }

    /**
     * Draw the silde.
     *
     * @param i slide index
     * @param stateObject
     * @return
     */
    public TrialResult doSlide (int i, SlideTrialExperimentState stateObject) {
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
        long taskId;
        try {
            taskId = currentTask.getTaskId();
        } catch (NullPointerException e){
            taskId = timeUtil.currentTimeMicros();
        }
        EventUtil.fireSlideOnEvent(i, slideOnLocalTime,
                slideEventListeners, taskId);

        // wait for current slide to finish
        do {
            if (!eyeController.isEyeIn()) {
                breakTrial(stateObject);
                currentContext.setAnimationFrameIndex(0);
                punisher.punish();
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
            } else{
            }
        } while (timeUtil.currentTimeMicros() < slideOnLocalTime
                + stateObject.getSlideLength() * 1000);

        // finish current slide
        drawingController.slideFinish(currentTask, currentContext);
        long slideOffLocalTime = timeUtil.currentTimeMicros();
        currentContext.setCurrentSlideOffTime(slideOffLocalTime);
        EventUtil.fireSlideOffEvent(i, slideOffLocalTime,
                currentContext.getAnimationFrameIndex(),
                slideEventListeners, taskId);
        currentContext.setAnimationFrameIndex(0);

        return TrialResult.SLIDE_OK;
    }


    public static TrialResult waitInterSlideInterval (SlideTrialExperimentState stateObject, ThreadHelper threadHelper) {
        TimeUtil timeUtil = stateObject.getLocalTimeUtil();
        TrialContext currentContext = stateObject.getCurrentContext();
        EyeController eyeController = stateObject.getEyeController();

        while (timeUtil.currentTimeMicros() < currentContext.getCurrentSlideOffTime()
                + stateObject.getInterSlideInterval() * 1000) {
            if (!eyeController.isEyeIn()) {
                breakTrial(stateObject);
                return TrialResult.EYE_BREAK;
            }
            if (threadHelper.isDone()) {
                return TrialResult.EXPERIMENT_STOPPING;
            }
        }
        return TrialResult.SLIDE_OK;
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


    public static void getNextTask(TrialExperimentState state) {
        state.setCurrentTask(state.getTaskDataSource().getNextTask());
    }

    public void setPunisher(Punisher punisher) {
        this.punisher = punisher;
    }
}
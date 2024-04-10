package org.xper.allen.ga;

import org.xper.classic.ClassicSlideRunner;
import org.xper.classic.SlideEventListener;
import org.xper.classic.SlideRunner;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialResult;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.EyeController;
import org.xper.experiment.TaskDoneCache;
import org.xper.time.TimeUtil;
import org.xper.util.EventUtil;
import org.xper.util.ThreadHelper;

import java.util.List;


public class MockNoDrawSlideRunner implements SlideRunner {
    @Override
    public TrialResult runSlides(SlideTrialExperimentState stateObject, ThreadHelper threadHelper) {
        int slidePerTrial = stateObject.getSlidePerTrial();
//        TrialDrawingController drawingController = stateObject.getDrawingController();
        ExperimentTask currentTask = stateObject.getCurrentTask();
        TrialContext currentContext = stateObject.getCurrentContext();
        TaskDoneCache taskDoneCache = stateObject.getTaskDoneCache();
        TimeUtil globalTimeClient = stateObject.getGlobalTimeClient();

        try {
            for (int i = 0; i < slidePerTrial; i++) {

                // draw the slide
                if (stateObject.getCurrentTask() == null){
                    return TrialResult.NO_MORE_TASKS;
                }

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
                    ClassicSlideRunner.getNextTask(stateObject);
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
                    currentContext.setSlideIndex(i + 1);
                    currentContext.setCurrentTask(currentTask);
//                    drawingController.prepareNextSlide(currentTask,
//                            currentContext);
                }
            }
            return TrialResult.TRIAL_COMPLETE;
            // end of SlideRunner.runSlide
        } finally {
            try {
                ClassicSlideRunner.cleanupTask(stateObject);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    public static TrialResult doSlide (int i, SlideTrialExperimentState stateObject) {
//        TrialDrawingController drawingController = stateObject.getDrawingController();
        ExperimentTask currentTask = stateObject.getCurrentTask();
        TrialContext currentContext = stateObject.getCurrentContext();
        List<? extends SlideEventListener> slideEventListeners = stateObject.getSlideEventListeners();
        EyeController eyeController = stateObject.getEyeController();
        TimeUtil timeUtil = stateObject.getLocalTimeUtil();

        // show current slide
        long slideOnLocalTime = timeUtil.currentTimeMicros();
        currentContext.setCurrentSlideOnTime(slideOnLocalTime);
        EventUtil.fireSlideOnEvent(i, slideOnLocalTime,
                slideEventListeners, currentTask.getTaskId());



        // finish current slide
        long slideOffLocalTime = timeUtil.currentTimeMicros();
        currentContext.setCurrentSlideOffTime(slideOffLocalTime);
        EventUtil.fireSlideOffEvent(i, slideOffLocalTime,
                currentContext.getAnimationFrameIndex(),
                slideEventListeners, currentTask.getTaskId());
        currentContext.setAnimationFrameIndex(0);

        return TrialResult.SLIDE_OK;
    }
}
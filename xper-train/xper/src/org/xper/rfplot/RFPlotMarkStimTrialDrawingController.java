package org.xper.rfplot;

import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;

public class RFPlotMarkStimTrialDrawingController extends MarkStimTrialDrawingController {

    public void animateSlide(ExperimentTask task, TrialContext context) {
        animateTaskScene(task, context);
        getWindow().swapBuffers();
    }

    protected void drawTaskScene(ExperimentTask task, Context context) {
        if (task != null) {
            getTaskScene().setTask(task);
            getTaskScene().drawTask(context, true);
        } else {
            getTaskScene().drawBlank(context, true, true);
        }
    }

    @Override
    protected void animateTaskScene(ExperimentTask task, Context context) {
        if (task != null) {
            getTaskScene().setTask(task);
            getTaskScene().drawTask(context, true);
        } else {
            getTaskScene().drawBlank(context, true, true);
        }
    }

}
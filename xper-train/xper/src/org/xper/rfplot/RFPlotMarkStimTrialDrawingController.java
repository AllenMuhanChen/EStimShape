package org.xper.rfplot;

import org.apache.commons.math3.analysis.function.Exp;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;
import org.xper.util.TrialExperimentUtil;

public class RFPlotMarkStimTrialDrawingController extends MarkStimTrialDrawingController {

    public void animateSlide(ExperimentTask task, TrialContext context) {
        animateTaskScene(task, context);
        getWindow().swapBuffers();
    }

    protected void drawTaskScene(ExperimentTask task, Context context) {
        if (task != null) {
            taskScene.setTask(task);
            taskScene.drawTask(context, true);
        } else {
            taskScene.drawBlank(context, true, true);
        }
    }

    @Override
    protected void animateTaskScene(ExperimentTask task, Context context) {
        if (task != null) {
            taskScene.setTask(task);
            taskScene.drawTask(context, true);
        } else {
            taskScene.drawBlank(context, true, true);
        }
    }

}

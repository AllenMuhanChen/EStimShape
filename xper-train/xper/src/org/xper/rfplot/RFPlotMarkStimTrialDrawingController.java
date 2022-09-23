package org.xper.rfplot;

import org.apache.commons.math3.analysis.function.Exp;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;

public class RFPlotMarkStimTrialDrawingController extends MarkStimTrialDrawingController {

    public void animateSlide(ExperimentTask task, TrialContext context) {
        animateTaskScene(task, context);
        getWindow().swapBuffers();
    }

    @Override
    protected void animateTaskScene(ExperimentTask task, Context context) {
        if (task != null) {
            taskScene.setTask(task);
            taskScene.drawTask(context, fixationOnWithStimuli);
        } else {
            taskScene.drawBlank(context, fixationOnWithStimuli, true);
        }
    }

}

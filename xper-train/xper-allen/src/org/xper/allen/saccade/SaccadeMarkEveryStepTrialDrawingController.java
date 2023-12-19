package org.xper.allen.saccade;

import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;

public class SaccadeMarkEveryStepTrialDrawingController extends MarkEveryStepTrialDrawingController{
	@Override
	public void slideFinish(ExperimentTask task, TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		getWindow().swapBuffers();
	}

}
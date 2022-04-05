package org.xper.allen.nafc.experiment;

import org.xper.classic.TrialDrawingController;
import org.xper.drawing.Context;

public interface NAFCTrialDrawingController extends TrialDrawingController{
	public void prepareSample(NAFCExperimentTask task, Context context);
	public void showSample(NAFCExperimentTask task, Context context);
	public void prepareChoice(NAFCExperimentTask task, Context context);
	public void showChoice(NAFCExperimentTask task, Context context);
	public void animateSample(NAFCExperimentTask task, Context context);
}

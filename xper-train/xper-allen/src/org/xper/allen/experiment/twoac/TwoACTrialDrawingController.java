package org.xper.allen.experiment.twoac;

import org.xper.classic.TrialDrawingController;
import org.xper.drawing.Context;

public interface TwoACTrialDrawingController extends TrialDrawingController{
	public void prepareSample(TwoACExperimentTask task, Context context);
	
	public void prepareChoice(TwoACExperimentTask task, Context context);
}

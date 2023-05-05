package org.xper.allen.nafc.experiment;

import org.xper.classic.TrialDrawingController;
import org.xper.drawing.Context;

public interface NAFCTrialDrawingController extends TrialDrawingController{
	public void prepareSample(NAFCExperimentTask task, NAFCTrialContext context);
	public void showSample(NAFCExperimentTask task, NAFCTrialContext context);

	public void showAnswer(NAFCExperimentTask task, NAFCTrialContext context);
	public void prepareChoice(NAFCExperimentTask task, NAFCTrialContext context);
	public void showChoice(NAFCExperimentTask task, NAFCTrialContext context);
	public void animateSample(NAFCExperimentTask task, NAFCTrialContext context);
	public void trialStart(NAFCTrialContext Context);
}

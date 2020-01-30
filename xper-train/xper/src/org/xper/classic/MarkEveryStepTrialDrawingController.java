package org.xper.classic;

import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;

public class MarkEveryStepTrialDrawingController extends
		MarkStimTrialDrawingController {
	
	public void trialStart(TrialContext context) {
		taskScene.trialStart(context);
		
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, true);
		window.swapBuffers();
	}
	
	public void prepareFixationOn(TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, true, true);
	}
	
	public void initialEyeInFail(TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, true);
		window.swapBuffers();
	}
	
	public void eyeInHoldFail(TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, true);
		window.swapBuffers();
	}
	
	public void slideFinish(ExperimentTask task, TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, true, true);
		window.swapBuffers();
	}

	public void eyeInBreak(TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, true);
		window.swapBuffers();
	}

	public void trialComplete(TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, true);
		window.swapBuffers();
	}

	public void trialStop(TrialContext context) {
		// show no markers during inter trial interval
		taskScene.drawBlank(context, false, false);
		window.swapBuffers();
		
		taskScene.trialStop(context);
	}
}

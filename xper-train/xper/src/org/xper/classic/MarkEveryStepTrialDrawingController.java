package org.xper.classic;

import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;

public class MarkEveryStepTrialDrawingController extends
		MarkStimTrialDrawingController {

	public void trialStart(TrialContext context) {
		getTaskScene().trialStart(context);

		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		getWindow().swapBuffers();
	}

	public void prepareFixationOn(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, true, true);
	}

	public void initialEyeInFail(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		getWindow().swapBuffers();
	}

	public void eyeInHoldFail(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		getWindow().swapBuffers();
	}

	public void slideFinish(ExperimentTask task, TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, true, true);
		getWindow().swapBuffers();
	}

	public void eyeInBreak(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		getWindow().swapBuffers();
	}

	public void trialComplete(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		getWindow().swapBuffers();
	}

	public void trialStop(TrialContext context) {
		// show no markers during inter trial interval
		getTaskScene().drawBlank(context, false, false);
		getWindow().swapBuffers();

		getTaskScene().trialStop(context);
	}
}
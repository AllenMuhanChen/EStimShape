package org.xper.allen.nafc.experiment;

import org.xper.Dependency;
import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.drawing.TaskScene;
import org.xper.experiment.ExperimentTask;

public class NAFCMarkEveryStepTrialDrawingController extends NAFCMarkStimTrialDrawingController implements NAFCTrialDrawingController{

	public void prepareSample(NAFCExperimentTask task, Context context) {
		if (task != null) {
			System.out.println(task);
			System.out.println(getTaskScene());
			getTaskScene().setSample(task);
//			getTaskScene().drawSample(context, true);
		} else {
			getTaskScene().drawBlank(context, false, false);
		}
	}
	
	@Override
	public void slideFinish(ExperimentTask task, TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		window.swapBuffers();
	}
	
	public void prepareChoice(NAFCExperimentTask task, Context context) {
		if (task != null) {
			getTaskScene().setChoice(task);
//			getTaskScene().drawChoice(context, false);
		} else {
			getTaskScene().drawBlank(context, false, false);
		}
	}

	//From MarkEveryStepTrialDrawingController
	
	public void trialStart(NAFCTrialContext context) {
		getTaskScene().trialStart(context);
		
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		window.swapBuffers();
	}
	
	public void prepareFixationOn(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, true, true);
	}
	
	public void initialEyeInFail(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		window.swapBuffers();
	}
	
	public void eyeInHoldFail(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		window.swapBuffers();
	}
	

	public void eyeInBreak(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		window.swapBuffers();
	}

	public void trialComplete(TrialContext context) {
		getTaskScene().nextMarker();
		getTaskScene().drawBlank(context, false, true);
		window.swapBuffers();
	}

	public void trialStop(TrialContext context) {
		// show no markers during inter trial interval
		getTaskScene().drawBlank(context, false, false);
		window.swapBuffers();
		
		getTaskScene().trialStop(context);
	}
	

}

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
			taskScene.setSample(task);
			taskScene.drawSample(context, true);
		} else {
			taskScene.drawBlank(context, false, false);
		}
	}
	
	@Override
	public void slideFinish(ExperimentTask task, TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, true);
		window.swapBuffers();
	}
	
	public void prepareChoice(NAFCExperimentTask task, Context context) {
		if (task != null) {
			taskScene.setChoice(task);
			taskScene.drawChoice(context, false);
		} else {
			taskScene.drawBlank(context, false, false);
		}
	}

	//From MarkEveryStepTrialDrawingController
	
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

package org.xper.allen.twoac;

import org.xper.Dependency;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;

public class TwoACMarkStimTrialDrawingController extends MarkStimTrialDrawingController implements TwoACTrialDrawingController{

	@Dependency
	protected TwoACTaskScene taskScene;
	
	boolean initialized = false;
	
	@Override
	public void slideFinish(ExperimentTask task, TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, false);
		window.swapBuffers();
	}
	
	public void prepareSample(TwoACExperimentTask task, Context context) {
		if (task != null) {
			taskScene.setSample(task);
			taskScene.drawSample(context, true);
		} else {
			taskScene.drawBlank(context, false, false);
		}
	}
	
	public void prepareChoice(TwoACExperimentTask task, Context context) {
		if (task != null) {
			taskScene.setChoice(task);
			taskScene.drawChoice(context, false);
		} else {
			taskScene.drawBlank(context, false, false);
		}
	}
	
	public TwoACTaskScene getTwoACTaskScene() {
		return taskScene;
	}

	public void setTaskScene(TwoACTaskScene taskScene) {
		this.taskScene = taskScene;
	}
	
	// not sure if below needed. 
	public void init() {
		window.create();
		taskScene.initGL(window.getWidth(), window.getHeight());
		initialized = true;
	}
	
	public void destroy() {
		if (initialized) {
			window.destroy();
			initialized = false;
		}
	}

	
}

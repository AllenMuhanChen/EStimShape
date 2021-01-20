package org.xper.allen.experiment.twoac;

import org.xper.Dependency;
import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Context;
import org.xper.drawing.TaskScene;
import org.xper.experiment.ExperimentTask;

public class TwoACMarkEveryStepTrialDrawingController extends MarkEveryStepTrialDrawingController{
	@Dependency
	protected TwoACTaskScene taskScene;
	
	@Override
	public void slideFinish(ExperimentTask task, TrialContext context) {
		taskScene.nextMarker();
		taskScene.drawBlank(context, false, true);
		window.swapBuffers();
	}
	
	protected void prepareSample(TwoACExperimentTask task, Context context) {
		if (task != null) {
			taskScene.setSample(task);
			System.out.println("Two");
			taskScene.drawSample(context, true);
			System.out.println("Three");
		} else {
			taskScene.drawBlank(context, false, false);
		}
	}
	
	protected void prepareChoice(TwoACExperimentTask task, Context context) {
		if (task != null) {
			taskScene.setChoice(task);
			taskScene.drawChoice(context, false);
		} else {
			taskScene.drawBlank(context, false, false);
		}
	}

	public TwoACTaskScene getTaskScene() {
		return taskScene;
	}
	

	public void setTaskScene(TwoACTaskScene taskScene) {
		this.taskScene = taskScene;
	}

}

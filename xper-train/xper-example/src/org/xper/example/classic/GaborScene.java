package org.xper.example.classic;

import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.drawing.RFPlotGratingObject;

public class GaborScene extends AbstractTaskScene {

	RFPlotGratingObject obj = new RFPlotGratingObject();

	public void initGL(int w, int h) {
		super.initGL(w, h);
		RFPlotGratingObject.initGL();
	}

	public void setTask(ExperimentTask task) {
		obj.setSpec(task.getStimSpec());
	}

	public void drawStimulus(Context context) {
		obj.draw(context);
	}
}
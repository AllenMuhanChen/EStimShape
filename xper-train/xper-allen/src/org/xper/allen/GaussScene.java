package org.xper.allen;

import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.RFPlotGaborObject;

public class GaussScene extends AbstractTaskScene{

	RFPlotGaussianObject obj = new RFPlotGaussianObject();
	
	public void initGL(int w, int h) {
		super.initGL(w, h);
		RFPlotGaussianObject.initGL();
	}

	public void setTask(ExperimentTask task) {
		obj.setSpec(task.getStimSpec());
	}

	public void drawStimulus(Context context) {
		obj.draw(context);
	}
	
}

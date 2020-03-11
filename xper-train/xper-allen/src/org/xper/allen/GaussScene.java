package org.xper.allen;

import org.xper.Dependency;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.RFPlotGaborObject;

public class GaussScene extends AbstractTaskScene{
	/**
	 * xper_monkey_screen_distance
	 */
	@Dependency
	double distance;
	RFPlotGaussianObject obj = new RFPlotGaussianObject(distance);
	
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

	public double getDistance() {
		return distance;
	}

	public void setDistance(double distance) {
		this.distance = distance;
	}
	
	
}

package org.xper.allen.saccade;

import org.xper.Dependency;
import org.xper.allen.drawing.RFPlotGaussianObject;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.experiment.ExperimentTask;

public class GaussScene extends AbstractTaskScene{
	/**
	 * xper_monkey_screen_distance
	 */
	@Dependency
	double distance;
	RFPlotGaussianObject obj = new RFPlotGaussianObject();
	
	public void initGL(int w, int h) {
		super.initGL(w, h);
		RFPlotGaussianObject.initGL();
	}

	public void setTask(ExperimentTask task) {
		obj.setSpec(task.getStimSpec());
	}

	public void drawStimulus(Context context) {
		obj.setDistance(distance);
		obj.draw(context);
	}

	public double getDistance() {
		return distance;
	}

	public void setDistance(double distance) {
		this.distance = distance;
	}
	
	
}

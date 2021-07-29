package org.xper.allen.twoac;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.allen.drawing.RFPlotGaussianObject;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;

public class TwoACGaussScene extends AbstractTaskScene implements TwoACTaskScene{
	/**
	 * xper_monkey_screen_distance
	 */
	@Dependency
	double distance;
	RFPlotGaussianObject[] objs = {new RFPlotGaussianObject(), new RFPlotGaussianObject(), new RFPlotGaussianObject()};
	
	public void initGL(int w, int h) {
		super.initGL(w, h);
		RFPlotGaussianObject.initGL();
	}

	public void setSample(TwoACExperimentTask task) {
		objs[0].setSpec(task.getSampleSpec());
	}
	

	public void setChoice(TwoACExperimentTask task) {
		objs[1].setSpec(task.getChoiceSpec()[0]);
		objs[2].setSpec(task.getChoiceSpec()[1]);
	}

	public void drawSample(Context context, final boolean fixationOn) {
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				drawSampleStimulus(context);
				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}
				
				if (fixationOn) {
					 fixation.draw(context);
				}
				marker.draw(context);
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
			}}, context);
	}

	public void drawSampleStimulus(Context context) {
		objs[0].setDistance(distance);
		objs[0].draw(context);
	}
	
	public void drawChoice(Context context, final boolean fixationOn) {
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				drawChoiceStimuli(context);
				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}
				
				if (fixationOn) {
					 fixation.draw(context);
				}
				marker.draw(context);
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
			}}, context);
	}
	
	public void drawChoiceStimuli(Context context) {
		objs[1].setDistance(distance);
		objs[1].draw(context);
		objs[2].setDistance(distance);
		objs[2].draw(context);
	}
	
	public double getDistance() {
		return distance;
	}

	public void setDistance(double distance) {
		this.distance = distance;
	}

	@Override
	public void setTask(ExperimentTask task) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void drawStimulus(Context context) {
		// TODO Auto-generated method stub
		
	}

	
	
}

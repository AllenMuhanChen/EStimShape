package org.xper.allen.nafc;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.allen.drawing.RFPlotGaussianObject;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;

public class NAFCGaussScene extends AbstractTaskScene implements NAFCTaskScene{
	/**
	 * xper_monkey_screen_distance
	 */
	@Dependency
	double distance;
	RFPlotGaussianObject sample = new RFPlotGaussianObject();
	RFPlotGaussianObject[] choices;
	int n;
	
	public void initGL(int w, int h) {
		super.initGL(w, h);
		RFPlotGaussianObject.initGL();
	}

	public void setSample(NAFCExperimentTask task) {
		sample.setSpec(task.getSampleSpec());
	}
	

	public void setChoice(NAFCExperimentTask task) {
		n = task.getChoiceSpec().length;
		for (int i = 0; i < n; i++){
			choices[i].setSpec(task.getChoiceSpec()[i]);
		}

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
		sample.setDistance(distance);
		sample.draw(context);
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
		
		for (int i = 0; i < n; i++){
			choices[i].setDistance(distance);
			choices[i].draw(context);
		}
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
	
	public void trialStart(NAFCTrialContext context) {
	}

	
	
}

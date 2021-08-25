package org.xper.allen.nafc;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.png.Image;
import org.xper.allen.drawing.png.ImageStack;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;

public class NAFCPngScene extends AbstractTaskScene implements NAFCTaskScene{
	Image sample;
	
	Image[] choices;
	ImageStack blankImage = new ImageStack();
	
	double screenWidth;
	double screenHeight;
	int numChoices;
	
	
	public void initGL(int w, int h) {
		super.setUseStencil(true);
		super.initGL(w, h);
//		
		//System.out.println("JK 32838 w = " + screenWidth + ", h = " + screenHeight);
		
		GL11.glClearColor(0.5f, 0.5f, 0.5f, 0.0f);          
		GL11.glViewport(0,0,w,h);
        GL11.glMatrixMode(GL11.GL_MODELVIEW); 
        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glLoadIdentity();
		
        GL11.glOrtho(0, w, h, 0, 1, -1);
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
	}

	public void trialStop(NAFCTrialContext context) {
		//choices.cleanUp();
		//sample.cleanUp();
	}
	
	@Override
	public void setSample(NAFCExperimentTask task) {
		sample = new Image();
		String sampleSpec = task.getSampleSpec();
		sample.loadTexture(sampleSpec);
	}

	@Override
	public void setChoice(NAFCExperimentTask task) {
		// TODO Auto-generated method stub
		String[] choiceSpec = task.getChoiceSpec();
		numChoices = choiceSpec.length;
		
		choices = new Image[numChoices];
		for (int i=0; i < numChoices; i++){
			choices[i] = new Image();
			choices[i].loadTexture(choiceSpec[i]);
		}
	}

	@Override
	public void drawSample(Context context, boolean fixationOn) {
		
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				sample.draw(context);
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
	

	@Override
	public void drawChoice(Context context, boolean fixationOn) {
		// TODO Auto-generated method stub
		// clear the whole screen before define view ports in renderer

		
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				for (int i = 0; i < numChoices; i++){
					choices[i].draw(context);
				}
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



	@Override
	public void setTask(ExperimentTask task) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void drawStimulus(Context context) {
		// TODO Auto-generated method stub
		
	}

	public double getScreenWidth() {
		return screenWidth;
	}

	public void setScreenWidth(double screenWidth) {
		this.screenWidth = screenWidth;
	}

	public double getScreenHeight() {
		return screenHeight;
	}

	public void setScreenHeight(double screenHeight) {
		this.screenHeight = screenHeight;
	}
	
}

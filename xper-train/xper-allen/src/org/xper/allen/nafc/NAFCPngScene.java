package org.xper.allen.nafc;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.allen.drawing.png.ImageStack;
import org.xper.allen.drawing.png.PngGAParams;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;

public class NAFCPngScene extends AbstractTaskScene implements NAFCTaskScene{

	ImageStack sample = new ImageStack();
	ImageStack choices = new ImageStack();
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
        
        // context is valid so load blanks
        blankImage.setScreenWidth(screenWidth);
        blankImage.setScreenHeight(screenHeight);
        blankImage.setNumFrames(4);
        blankImage.genTextures();

	}

	public void trialStop(NAFCTrialContext context) {
		choices.cleanUp();
		sample.cleanUp();
	}
	
	@Override
	public void setSample(NAFCExperimentTask task) {
		String sampleSpec = task.getSampleSpec();
		sample.setNumFrames(1);
		sample.genTextures();
		sample.loadTexture(sampleSpec, 0);
	}

	@Override
	public void setChoice(NAFCExperimentTask task) {
		// TODO Auto-generated method stub
		String[] choiceSpec = task.getChoiceSpec();
		numChoices = choiceSpec.length;
		choices.setNumFrames(numChoices);
		choices.setFrameNum(0);
		choices.genTextures();
		for (int i=0; i < numChoices; i++){
			choices.loadTexture(choiceSpec[i], i);
		}
	}

	@Override
	public void drawSample(Context context, boolean fixationOn) {
		sample.draw(context);
		
	}

	@Override
	public void drawChoice(Context context, boolean fixationOn) {
		// TODO Auto-generated method stub
		// clear the whole screen before define view ports in renderer
		for (int i = 0; i < numChoices; i++){
			choices.draw(context);
		}
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

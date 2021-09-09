package org.xper.allen.nafc;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.allen.drawing.png.TranslatableImages;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.specs.PngSpec;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;

public class NAFCPngScene extends AbstractTaskScene implements NAFCTaskScene{
	@Dependency
	int numChoices;
	@Dependency
	double distance;
	@Dependency
	double screenWidth;
	@Dependency
	double screenHeight;

	TranslatableImages images; 
	
	Coordinates2D[] choiceLocations;
	Coordinates2D sampleLocation;
	
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

	public void trialStart(TrialContext context) {
		images = new TranslatableImages(numChoices + 1);
		images.initTextures();
	}
	
	@Override
	public void setSample(NAFCExperimentTask task) {
		PngSpec sampleSpec = PngSpec.fromXml(task.getSampleSpec());
		sampleLocation = new Coordinates2D(sampleSpec.getxCenter(), sampleSpec.getyCenter());
		images.loadTexture(sampleSpec.getPath(), 0);
	}

	@Override
	public void setChoice(NAFCExperimentTask task) {
		// TODO Auto-generated method stub
		String[] choiceSpecXml = task.getChoiceSpec();
		numChoices = choiceSpecXml.length;
		PngSpec[] choiceSpec = new PngSpec[numChoices];
		choiceLocations = new Coordinates2D[numChoices];
		for (int i=0; i < numChoices; i++) {
			choiceSpec[i] = PngSpec.fromXml(choiceSpecXml[i]);
			choiceLocations[i] = new Coordinates2D(choiceSpec[i].getxCenter(), choiceSpec[i].getyCenter());
		}
		
		for (int i=0; i < numChoices; i++){
			images.loadTexture(choiceSpec[i].getPath(),i+1);
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
				images.draw(context, 0, sampleLocation);
				images.cleanUpImage(0);
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
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				for (int i = 0; i < numChoices; i++){
					//System.out.println();
					images.draw(context,i+1, choiceLocations[i]);
					images.cleanUpImage(i+1);
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


	public double getDistance() {
		return distance;
	}


	public void setDistance(double distance) {
		this.distance = distance;
	}


	public int getNumChoices() {
		return numChoices;
	}


	public void setNumChoices(int numChoices) {
		this.numChoices = numChoices;
	}
	
}

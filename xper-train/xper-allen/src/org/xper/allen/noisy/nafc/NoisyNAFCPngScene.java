package org.xper.allen.noisy.nafc;

import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.NAFCTaskScene;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.allen.noisy.NoisyTranslatableResizableImages;
import org.xper.allen.specs.PngSpec;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;

public class NoisyNAFCPngScene extends AbstractTaskScene implements NAFCTaskScene{
	@Dependency
	int numChoices;
	@Dependency
	double distance;
	@Dependency
	double screenWidth;
	@Dependency
	double screenHeight;
	@Dependency
	double[] backgroundColor;
	@Dependency
	int frameRate = Display.getDisplayMode().getFrequency();
	/**
	 * We keep this just one images object rather than one for choices and one for sample
	 * because OpenGL binds textures to integer IDs when we preload images. So if
	 * there are two separate objects, IDs would conflict. 
	 */
	NoisyTranslatableResizableImages images; 
	
	Coordinates2D[] choiceLocations;
	Coordinates2D sampleLocation;
	ImageDimensions sampleDimensions;
	ImageDimensions[] choiceDimensions;
	double[] choiceAlphas;
	
	public void initGL(int w, int h) {
		
		super.setUseStencil(true);
		super.initGL(w, h);
		//System.out.println("JK 32838 w = " + screenWidth + ", h = " + screenHeight);
		
		GL11.glClearColor((float)backgroundColor[0], (float)backgroundColor[1], (float)backgroundColor[2], 0.0f);
		//The below is unncessary stuff that gets overidden later
//		GL11.glViewport(0,0,w,h);
//        GL11.glMatrixMode(GL11.GL_PROJECTION);
//        GL11.glLoadIdentity();
//		
//        GL11.glOrtho(0, w, h, 0, 1, -1);
//        GL11.glMatrixMode(GL11.GL_MODELVIEW);
		
	}

	public void trialStart(NAFCTrialContext context) {
//		System.out.println("AC 23948902342: " + frameRate);
		NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
		numChoices = task.getChoiceSpec().length;
		int numFrames = (int) (context.getSampleLength()/1000 * frameRate);
		images = new NoisyTranslatableResizableImages(numFrames, numChoices + 1);
		images.initTextures();

	}
	
	@Override
	public void setSample(NAFCExperimentTask task) {
		PngSpec sampleSpec = PngSpec.fromXml(task.getSampleSpec());
		sampleLocation = new Coordinates2D(sampleSpec.getxCenter(), sampleSpec.getyCenter());
		sampleDimensions = sampleSpec.getImageDimensions();
//		System.out.println(images);
		images.loadTexture(sampleSpec.getPath(), 0);
		images.loadNoise(0);
	}

	@Override
	public void setChoice(NAFCExperimentTask task) {
		String[] choiceSpecXml = task.getChoiceSpec();
		numChoices = choiceSpecXml.length;
		PngSpec[] choiceSpec = new PngSpec[numChoices];
		choiceLocations = new Coordinates2D[numChoices];
		choiceDimensions = new ImageDimensions[numChoices];
		choiceAlphas= new double[numChoices];
		for (int i=0; i < numChoices; i++) {
			choiceSpec[i] = PngSpec.fromXml(choiceSpecXml[i]);
			choiceLocations[i] = new Coordinates2D(choiceSpec[i].getxCenter(), choiceSpec[i].getyCenter());
			choiceDimensions[i] = choiceSpec[i].getImageDimensions();
			choiceAlphas[i] = choiceSpec[i].getAlpha();
		}

		for (int i=0; i < numChoices; i++){
			images.loadTexture(choiceSpec[i].getPath(),i+1, choiceAlphas[i]);
		}
	}

	
	public void drawSample(Context context, boolean fixationOn) {
		
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) { 
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				int index = 0; //Should be zero, the sample is assigned index of zero. 
				images.draw(true, context, index, sampleLocation, sampleDimensions);
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
					images.draw(false, context,i+1, choiceLocations[i], choiceDimensions[i]);
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


	public void trialStop(Context context) {
		for (int i=0; i<numChoices+1; i++) {
			images.cleanUpImage(i);
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

	public double[] getBackgroundColor() {
		return backgroundColor;
	}

	public void setBackgroundColor(double[] backgroundColor) {
		this.backgroundColor = backgroundColor;
	}

	public int getFrameRate() {
		return frameRate;
	}

	public void setFrameRate(int frameRate) {
		this.frameRate = frameRate;
	}
	
}

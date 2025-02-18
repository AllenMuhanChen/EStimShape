package org.xper.allen.noisy.nafc;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.allen.nafc.NAFCTaskScene;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.allen.noisy.NoisyTranslatableResizableImages;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;

import java.awt.*;

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
	int frameRate;
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
	private int numFrames;
	private Color color;

	@Override
	public void initGL(int w, int h) {

		setUseStencil(true);
		super.initGL(w, h);
		GL11.glViewport(0,0,w,h);
	}

	@Override
	public void trialStart(NAFCTrialContext context) {
		NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
		numChoices = task.getChoiceSpec().length;

		//Choose numNoiseFrames
		NoisyPngSpec sampleSpec = NoisyPngSpec.fromXml(task.getSampleSpec());
		double noiseRate = sampleSpec.getNoiseRate();
//		double playRate = Math.ceil(noiseRate * frameRate);
		long duration = context.getSampleLength()+100; //100 ms buffer
		double durationSeconds = duration/1000.0;
		numFrames = (int) Math.ceil((durationSeconds*frameRate));

		System.out.println("numFrames: " + numFrames);

		images = new NoisyTranslatableResizableImages(numFrames, numChoices + 1, noiseRate);
		images.initTextures();
	}

	@Override
	public void setSample(NAFCExperimentTask task) {
		NoisyPngSpec sampleSpec = NoisyPngSpec.fromXml(task.getSampleSpec());
		sampleLocation = new Coordinates2D(sampleSpec.getxCenter(), sampleSpec.getyCenter());
		sampleDimensions = sampleSpec.getImageDimensions();
		color = sampleSpec.getColor();
		images.loadTexture(sampleSpec.getPath(), 0);
		String noiseMapPath = sampleSpec.getNoiseMapPath();

		images.loadNoise(noiseMapPath, color);
	}

	@Override
	public void setChoice(NAFCExperimentTask task) {
		String[] choiceSpecXml = task.getChoiceSpec();
		numChoices = choiceSpecXml.length;
		NoisyPngSpec[] choiceSpec = new NoisyPngSpec[numChoices];
		choiceLocations = new Coordinates2D[numChoices];
		choiceDimensions = new ImageDimensions[numChoices];
		choiceAlphas= new double[numChoices];
		for (int i=0; i < numChoices; i++) {
			choiceSpec[i] = NoisyPngSpec.fromXml(choiceSpecXml[i]);
			choiceLocations[i] = new Coordinates2D(choiceSpec[i].getxCenter(), choiceSpec[i].getyCenter());
			choiceDimensions[i] = choiceSpec[i].getImageDimensions();
			choiceAlphas[i] = choiceSpec[i].getAlpha();
		}

		for (int i=0; i < numChoices; i++){
			images.loadTexture(choiceSpec[i].getPath(),i+1, choiceAlphas[i]);
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
				int pngIndex = 0; //Should be zero, the sample is assigned index of zero.
				images.draw(true, context, pngIndex, sampleLocation, sampleDimensions);
				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}

				if (fixationOn) {
					 getFixation().draw(context);
				}
				marker.draw(context);
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
			}}, context);
	}

	@Override
	public void drawBlank(Context context, final boolean fixationOn, final boolean markerOn) {


		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}
				if (fixationOn) {
					System.out.println("fixation: " + getFixation());
					getFixation().draw(context);
				}
				if (markerOn) {
					marker.draw(context);
				} else {
					marker.drawAllOff(context);
				}
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				drawCustomBlank(context);
			}}, context);
	}

	@Override
	public void drawChoice(Context context, boolean fixationOn, int i){
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}

				//System.out.println();
				images.draw(false, context,i+1, choiceLocations[i], choiceDimensions[i]);

				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}

				if (fixationOn) {
					getFixation().draw(context);
				}
				marker.draw(context);
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
			}}, context);
	}

	@Override
	public void drawChoices(Context context, boolean fixationOn) {
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
					 getFixation().draw(context);
				}
				marker.draw(context);
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
			}}, context);
	}


	@Override
	public void trialStop(TrialContext context) {
		if (images != null) {
			images.cleanUpImage();
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

	public Drawable getFixation(){
		return super.getFixation();
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

	public int getFrameRate() {
		return frameRate;
	}

	public void setFrameRate(int frameRate) {
		this.frameRate = frameRate;
	}

}
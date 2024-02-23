package org.xper.allen.app.fixation;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.*;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.TranslatableResizableImages;
import org.xper.rfplot.drawing.png.PngSpec;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.ExperimentTask;


public class PngScene extends AbstractTaskScene{
	@Dependency
	double distance;
	@Dependency
	double screenWidth;
	@Dependency
	double screenHeight;

	TranslatableResizableImages image;

	Coordinates2D pngLocation;
	ImageDimensions pngDimensions;
	double pngAlpha;

	public void trialStart(TrialContext context) {
		image = new TranslatableResizableImages(1);
		image.initTextures();
	}

	public void initGL(int w, int h) {

		super.setUseStencil(true);
		super.initGL(w, h);
		//System.out.println("JK 32838 w = " + screenWidth + ", h = " + screenHeight);
		GL11.glViewport(0,0,w,h);
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
        GL11.glMatrixMode(GL11.GL_PROJECTION);
        GL11.glLoadIdentity();

        GL11.glOrtho(0, w, h, 0, 1, -1);
        GL11.glMatrixMode(GL11.GL_MODELVIEW);
	}

	public void setTask(ExperimentTask task) {
		PngSpec pngSpec = PngSpec.fromXml(task.getStimSpec());
		pngLocation = new Coordinates2D(pngSpec.getxCenter(), pngSpec.getyCenter());
		pngDimensions = pngSpec.getDimensions();
		image.loadTexture(pngSpec.getPath(), 0);
	}

	public void drawTask(Context context, final boolean fixationOn) {
		// clear the whole screen before define view ports in renderer
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				drawStimulus(context);
				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}

				if (true) {
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
	public void drawStimulus(Context context) {

		int index = 0; //Should be zero, the sample is assigned index of zero.
		image.draw(context, index, pngLocation, pngDimensions);

	}

	public double getDistance() {
		return distance;
	}

	public void setDistance(double distance) {
		this.distance = distance;
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

	public TranslatableResizableImages getImage() {
		return image;
	}

	public void setImage(TranslatableResizableImages image) {
		this.image = image;
	}
}
package org.xper.allen.app.fixation;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.allen.noisy.NoisyTranslatableResizableImages;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.drawing.png.ImageDimensions;

public class NoisyPngScene extends AbstractTaskScene{

    @Dependency
    int frameRate;

    @Dependency
    int slideLength;

    @Dependency
    double[] backgroundColor;

    private NoisyTranslatableResizableImages image;
    private Coordinates2D stimLocation;
    private ImageDimensions stimDimensions;
    private int noiseIndx;
    private int numNoiseFrames;

    @Override
    public void initGL(int w, int h) {
        setUseStencil(true);
        super.initGL(w, h);

        GL11.glClearColor((float) getBackgroundColor()[0], (float) getBackgroundColor()[1], (float) getBackgroundColor()[2], 0.0f);
        GL11.glViewport(0,0,w,h);

    }

    @Override
    public void trialStart(TrialContext context){
        double durationSeconds = slideLength/1000.0;
        numNoiseFrames = (int) Math.ceil((durationSeconds* getFrameRate()));
        image = new NoisyTranslatableResizableImages(1, 1 );
        image.initTextures();
        noiseIndx = 0;
    }

    public double[] getBackgroundColor() {
        return backgroundColor;
    }

    public int getFrameRate() {
        return frameRate;
    }

    @Override
    public void setTask(ExperimentTask task) {
        NoisyPngSpec spec = NoisyPngSpec.fromXml(task.getStimSpec());
        stimLocation = new Coordinates2D(spec.getxCenter(), spec.getyCenter());
        stimDimensions = spec.getImageDimensions();
        image.loadTexture(spec.getPath(),0);
        String noiseMapPath = spec.getNoiseMapPath();
        image.loadNoise(noiseMapPath,0);
    }

    @Override
    public void drawStimulus(Context context) {
        // clear the whole screen before define view ports in renderer
        blankScreen.draw(null);
        renderer.draw(new Drawable() {
            public void draw(Context context) {
                if (useStencil) {
                    // 0 will pass for stimulus region
                    GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
                }
                int pngIndex = 0; //Should be zero
                image.draw(noiseIndx, context, pngIndex, stimLocation, stimDimensions);
                nextNoise();
                if (useStencil) {
                    // 1 will pass for fixation and marker regions
                    GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
                }

                getFixation().draw(context);

                marker.draw(context);
                if (useStencil) {
                    // 0 will pass for stimulus region
                    GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
                }
            }}, context);
    }

    public void nextNoise() {
        if (noiseIndx + 1 > numNoiseFrames)
            noiseIndx=0;
        this.noiseIndx++;
    }

    @Override
    public void trialStop(TrialContext context) {
        image.cleanUpImage();

    }


    public void setBackgroundColor(double[] backgroundColor) {
        this.backgroundColor = backgroundColor;
    }

    public void setFrameRate(int frameRate) {
        this.frameRate = frameRate;
    }
}


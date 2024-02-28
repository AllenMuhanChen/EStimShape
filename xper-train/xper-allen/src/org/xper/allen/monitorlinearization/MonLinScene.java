package org.xper.allen.monitorlinearization;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.*;
import org.xper.experiment.ExperimentTask;

public class MonLinScene extends AbstractTaskScene {

    private MonLinSpec spec;

    @Override
    public void setTask(ExperimentTask task) {
        spec = MonLinSpec.fromXml(task.getStimSpec());
    }

    @Override
    public void drawStimulus(Context context) {
        RGBColor color = spec.color;
        GL11.glClearColor(color.getRed(), color.getGreen(), color.getBlue(), 1.0f);
        GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
    }

    @Override
    /**
     * Don't draw fixation
     */
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

}
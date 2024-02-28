package org.xper.allen.monitorlinearization;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.GLUtil;
import org.xper.drawing.RGBColor;
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
}
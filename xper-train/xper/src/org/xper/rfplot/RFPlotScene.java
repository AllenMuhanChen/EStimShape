package org.xper.rfplot;

import java.util.Map;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
//import org.xper.drawing.renderer.PerspectiveStereoRenderer;
import org.xper.experiment.ExperimentTask;
import org.xper.rfplot.drawing.RFPlotBlankObject;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class RFPlotScene extends AbstractTaskScene {
	@Dependency
	Map<String, RFPlotDrawable> rfObjectMap;

	RFPlotStimSpec spec;
	RFPlotXfmSpec xfm;

	public void initGL(int w, int h) {
		super.initGL(w, h);
		// TODO: initGL for objects

	}

	public void setTask(ExperimentTask task) {
		spec = RFPlotStimSpec.fromXml(task.getStimSpec());
		if (spec != null) {
			String objClass = spec.getStimClass();
			RFPlotDrawable obj = rfObjectMap.get(objClass);
			if (obj != null) {
				obj.setSpec(spec.getStimSpec());
			}
		} else{
			String objClass = RFPlotBlankObject.class.getName();
			RFPlotDrawable obj = rfObjectMap.get(objClass);
			obj.setDefaultSpec();
		}
		xfm = RFPlotXfmSpec.fromXml(task.getXfmSpec());
	}

	public void drawStimulus(Context context) {
		if (spec == null) return;

		GL11.glShadeModel(GL11.GL_SMOOTH);
		GL11.glDisable(GL11.GL_DEPTH_TEST);

		String objClass = spec.getStimClass();
		RFPlotDrawable obj = rfObjectMap.get(objClass);
		if (obj != null) {
			GL11.glPushAttrib(GL11.GL_ALL_ATTRIB_BITS);
			GL11.glPushMatrix();
			// Enable blending
			GL11.glEnable(GL11.GL_BLEND);
			// Set blending function to approximate color multiplication
			GL11.glColor3f(xfm.getColor().getRed(), xfm.getColor().getGreen(), xfm.getColor().getBlue());


			GL11.glTranslated(xfm.getTranslation().getX(), xfm.getTranslation().getY(), 1.0);
			GL11.glRotatef(xfm.getRotation(), 0.0f, 0.0f, 1.0f);
			GL11.glScaled(xfm.getScale().getX(), xfm.getScale().getY(), 1.0);

			GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT | GL11.GL_STENCIL_BUFFER_BIT);
			obj.draw(context);

			GL11.glPopMatrix();
			GL11.glPopAttrib();
		}
	}

	public Map<String, RFPlotDrawable> getRfObjectMap() {
		return rfObjectMap;
	}

	public void setRfObjectMap(Map<String, RFPlotDrawable> rfObjectMap) {
		this.rfObjectMap = rfObjectMap;
	}
}
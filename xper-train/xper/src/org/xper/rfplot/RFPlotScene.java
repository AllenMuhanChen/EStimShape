package org.xper.rfplot;

import java.util.HashMap;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
//import org.xper.drawing.renderer.PerspectiveStereoRenderer;
import org.xper.experiment.ExperimentTask;

public class RFPlotScene extends AbstractTaskScene {
	@Dependency
	HashMap<String, RFPlotDrawable> rfObjectMap;
	
	RFPlotStimSpec spec;
	RFPlotXfmSpec xfm;

	public void initGL(int w, int h) {
//		renderer = (PerspectiveStereoRenderer)this.renderer;
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
		}
		xfm = RFPlotXfmSpec.fromXml(task.getXfmSpec());
	}

	public void drawStimulus(Context context) {
		if (spec == null) return;
		
		String objClass = spec.getStimClass();
		RFPlotDrawable obj = rfObjectMap.get(objClass);
		if (obj != null) {
			GL11.glPushAttrib(GL11.GL_ALL_ATTRIB_BITS);
			GL11.glColor3f(xfm.getColor().getRed(), xfm.getColor().getGreen(), xfm.getColor().getBlue());
			GL11.glPushMatrix();
			GL11.glTranslated(xfm.getTranslation().getX(), xfm.getTranslation().getY(), 1.0);
			GL11.glRotatef(xfm.getRotation(), 0.0f, 0.0f, 1.0f);
			GL11.glScaled(xfm.getScale().getX(), xfm.getScale().getY(), 1.0);
			
			obj.draw(context);
			
			GL11.glPopMatrix();
			GL11.glPopAttrib();
		}
	}
	
	public HashMap<String, RFPlotDrawable> getRfObjectMap() {
		return rfObjectMap;
	}

	public void setRfObjectMap(HashMap<String, RFPlotDrawable> rfObjectMap) {
		this.rfObjectMap = rfObjectMap;
	}
}

package org.xper.drawing.renderer;

import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.GLU;

public class PerspectiveIdenticalStereoRenderer extends StereoRenderer {
	
	@Override
	protected void setupLeft() {
		GL11.glViewport(0, 0, vpWidth, vpHeight);
		setupPerspective();
	}

	@Override
	protected void setupRight() {
		GL11.glViewport(vpWidth, 0, vpWidth, vpHeight);
		setupPerspective();
	}

	protected void setupPerspective () {
		GL11.glMatrixMode (GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double bottom = ymin * PROJECTION_NEAR / distance;
		double top = (ymax + vunit) * PROJECTION_NEAR / distance;
		if (inverted) {
			double left = xmax * PROJECTION_NEAR / distance;
			double right = (xmin - hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
		} else {
			double left = xmin * PROJECTION_NEAR / distance;
			double right = (xmax + hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
		}

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		//GL11.glTranslated (0, 0, -distance);
		GLU.gluLookAt (0, 0, (float)distance, 0, 0, 0, 0, 1, 0);
	}
}

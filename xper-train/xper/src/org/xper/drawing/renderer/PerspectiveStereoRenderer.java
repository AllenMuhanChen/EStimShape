package org.xper.drawing.renderer;

import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.GLU;

public class PerspectiveStereoRenderer extends StereoRenderer {

	@Override
	protected void setupLeft() {
		GL11.glViewport (0, 0, vpWidth, vpHeight);

		GL11.glMatrixMode (GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double bottom = ymin * PROJECTION_NEAR / distance;
		double top = (ymax + vunit) * PROJECTION_NEAR / distance;
		if (inverted) {
			double left = xmax * PROJECTION_NEAR / distance;
			double right = (xmin - hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
//			System.out.println("leftport: " + left + ", " + right + ", " + bottom + ", " + top + ", " + PROJECTION_NEAR + ", " + distance + ", " + depth);
		} else {
			double left = xmin * PROJECTION_NEAR / distance;
			double right = (xmax + hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
		}

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
//		GLU.gluLookAt ((float)le_pos, 0, (float)distance, 0, 0, 0, 0, 1, 0);
		GLU.gluLookAt (0, 0, (float)distance, 0, 0, 0, 0, 1, 0);

	}

	@Override
	protected void setupRight() {
		GL11.glViewport(vpWidth, 0, vpWidth, vpHeight);

		GL11.glMatrixMode (GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double bottom = ymin * PROJECTION_NEAR / distance;
		double top = (ymax + vunit) * PROJECTION_NEAR / distance;
		if (inverted) {
			double left = xmax * PROJECTION_NEAR / distance;
			double right = (xmin - hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
//			System.out.println("rightport: " + left + ", " + right + ", " + bottom + ", " + top + ", " + PROJECTION_NEAR + ", " + distance + ", " + depth);
		} else {
			double left = xmin * PROJECTION_NEAR / distance;
			double right = (xmax + hunit) * PROJECTION_NEAR / distance;
			GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);
		}

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		// GLU.gluLookAt ((float)re_pos, 0, (float)distance, 0, 0, 0, 0, 1, 0);
		GLU.gluLookAt (0, 0, (float)distance, 0, 0, 0, 0, 1, 0);
	}
}

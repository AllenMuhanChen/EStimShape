package org.xper.alden.drawing.renderer;

import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;

public class PerspectiveRenderer extends AbstractRenderer {
	public void init() {
		super.init();
		setup();
	}

	private void setup() {
		GL11.glMatrixMode(GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double left = xmin * PROJECTION_NEAR / distance;
		double right = (xmax + hunit) * PROJECTION_NEAR / distance;
		double bottom = ymin * PROJECTION_NEAR / distance;
		double top = (ymax + vunit) * PROJECTION_NEAR / distance;
		GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		GL11.glTranslated (0, 0, -distance);

	}

	public void draw(Drawable scene) {
//		setup();
		scene.draw();
	}

}